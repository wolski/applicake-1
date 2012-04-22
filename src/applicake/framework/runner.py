#!/bin/env python

'''
Created on Nov 11, 2010

@author: quandtan
'''

import os
import shutil
import sys
from cStringIO import StringIO
from subprocess import Popen
from subprocess import PIPE
from applicake.framework.argshandler import ApplicationArgsHandler
from applicake.framework.argshandler import WrapperArgsHandler
from applicake.framework.logger import Logger
from applicake.framework.interfaces import IApplication
from applicake.framework.interfaces import IWrapper
from applicake.framework.informationhandler import BasicInformationHandler
from applicake.utils.fileutils import FileUtils
from applicake.utils.fileutils import FileLocker
from applicake.utils.dictutils import DictUtils                          
                 
                 
class Runner(object):
    """
    Basic class to prepare and run one of the Interface classes of the framework as workflow node    
    """                      

    def __call__(self, args,app):
        """
        Program logic of the Application class.
        First, the command line arguments are parsed and validated. 
        Then, the main program logic is executed.
        
        Return: exit code (integer)
        """      
        default_info = {
                        'STORAGE':'memory',
                        'LOG_LEVEL':'DEBUG',
                        'NAME': app.__class__.__name__,
                        'CREATED_FILES': None
                        } 
        tmp_log_stream = StringIO()
        try:
            # create memory logger            
            log = Logger(level='DEBUG',name='memory_logger',stream=tmp_log_stream).logger
            log.debug('created temporary in-memory logger')
            # get command line arguments
            args = sys.argv
            log.debug('application class file [%s]' % args[0])
            log.debug('arguments [%s]' % args[1:])
            log.debug('Runner class [%s]' % self.__class__.__name__)
            log.debug('Application class [%s]' % app.__class__.__name__)
            log.debug('Start [%s]' % self.get_args_handler.__name__)
            args_handler = self.get_args_handler()
            log.debug('Finished [%s]' % self.get_args_handler.__name__)            
            log.debug('Start [%s]' % args_handler.get_parsed_arguments.__name__)
            pargs = args_handler.get_parsed_arguments()
            log.debug('Finish [%s]' % args_handler.get_parsed_arguments.__name__) 
            log.debug('Start [%s]' % self.get_info_handler.__name__)
            info_handler = self.get_info_handler()
            log.debug('Finished [%s]' % self.get_info_handler.__name__)
            log.debug('Start [%s]' % info_handler.get_info.__name__)
            info = info_handler.get_info(log, pargs)
            log.debug('Finished [%s]' % info_handler.get_info.__name__)
            log.debug('content of info [%s]' % info)
            info = DictUtils.merge(info, default_info,priority='left')
            log.debug('Added default values to info they were not set before')            
            log.debug('content of final info [%s]' % info)                   
            self.out_stream,self.err_stream,self.log_stream = self.get_streams(info,log)               
            sys.stdout = self.out_stream
            sys.stderr = self.err_stream
            log.debug('redirect sys streams for stdout/stderr depending on the chosen storage type')                       
            log = Logger(level=info['LOG_LEVEL'],
                         name=info['NAME'],stream=self.log_stream).logger       
            log.debug('created new logger dependent of the storage')
            tmp_log_stream.seek(0)
            self.log_stream.write(tmp_log_stream.read())
            log.debug('wrote content of temporary logger to new logger')                
            log.info('Start [%s]' % self.create_workdir.__name__)
            self.create_workdir(info,log) 
            log.info('Finished [%s]' % self.create_workdir.__name__)
            log.info('Start [%s]' % self.run_app.__name__)
            exit_code,info = self.run_app(app,info,log)
            log.debug('runner: content of info [%s]' % info)
            log.info('Finished [%s]' % self.run_app.__name__)               
            log.info('Start [%s]' % info_handler.write_info.__name__)
            info_handler.write_info(info,log)
            log.info('Finished [%s]' % info_handler.write_info.__name__)
            log.info('Start [%s]' % self._cleanup.__name__)
            self._cleanup(info,log)
            log.info('Finished [%s]' % self._cleanup.__name__)                               
            log.info('exit_code [%s]' % exit_code)
            self.info = info
            self.log = log
            return int(exit_code)
        except:
            self.reset_streams()
            if hasattr(self, 'log_stream'):
                stream = self.log_stream
            else:
                stream = tmp_log_stream    
            stream.seek(0)
            for line in stream.readlines():
                sys.stderr.write(line)
            raise   
    
    def _cleanup(self,info,log):
        """
        Does the final clean-up
        
        - copies input files and output file to working dir
        - moves created files to working dir
        - If storage='memory' is used, out and err stream are printed to stdout
        and log stream is printed to stderr
        
        Arguments:
        - info: Configuration object to access file and parameter information 
        - log: Logger to Logger to store log messages               
        """ 
        wd = info['WORKDIR']
        log.debug('start copying/moving files to work dir')
        # copy input files to working directory
        files_to_copy = []
        if info.has_key('INPUTS'):
            DictUtils.get_flatten_sequence([files_to_copy,info["INPUTS"]])
            log.debug('found following input files to copy [%s]' % info["INPUTS"])
        if info.has_key('OUTPUT'):
            DictUtils.get_flatten_sequence([files_to_copy,info["OUTPUT"]])
            log.debug('found following output files to copy [%s]' % info["OUTPUT"])            
        for path in files_to_copy:
            # 'r' escapes special characters
            src = r'%s' % os.path.abspath(path) 
            try:
                shutil.copy(src,wd) 
                log.debug('Copied [%s] to [%s]' % (src,wd))
            except:
                log.critical('Counld not copy [%s] to [%s]' % (src,wd))
                sys.exit(1)             
        self.reset_streams()  
        if info['STORAGE'] == 'memory':
            print '=== stdout ==='
            self.out_stream.seek(0)
            for line in self.out_stream.readlines():
                print line
            print '=== stderr ==='
            self.err_stream.seek(0)
            for line in self.err_stream.readlines():
                print line
            self.log_stream.seek(0)                
            for line in self.log_stream.readlines():
                sys.stderr.write(line)                    
        # move created files to working directory
        # 'created_files might be none e.g. if memory-storage is used   
        if info['CREATED_FILES'] is not None:  
            for path in info['CREATED_FILES']:
                src = r'%s' % os.path.abspath(path) 
                dest = r'%s' % os.path.join(wd,os.path.basename(path))
                try:
                    shutil.move(src,wd)
                    print('Move [%s] to [%s]' % (src,dest))
                except:
                    sys.stderr.write('Could not move [%s] to [%s]' % (src,dest))
                    sys.exit(1)  
                    
    def _set_jobid(self,info,log):
        """
        Uses a file-based system to retrieve a job id.
        
        Creates a file in a base dir that holds the last job id and increases it incrementally.
        If the 'jobid.txt' does not exists, it is initiated with the job id '1'.
        
        @type info: dict         
        @param info: Dictionary object with information needed by the class
        @type log: Logger 
        @param log: Logger to store log messages  
        """
        jobid = 1
        if not info.has_key('BASEDIR'):
            log.error("info has not key ['BASEDIR']. Therefore jobid is set to default=1")
        else:    
            dirname = info['BASEDIR']
            log.debug('found base dir [%s]' % dirname)
            filename = os.path.join(dirname, 'jobid.txt')
            locker = FileLocker()
            if (os.path.exists(filename)):            
                fh = open(filename,'r') 
                locker.lock(fh,locker.LOCK_EX) 
                jobid= int(fh.read())   
                log.debug('previous job id [%s]' % jobid)
                jobid += 1         
                log.debug('current job id [%s]' % jobid)
            fh = open(filename,'w')    
            fh.write(str(jobid))
            locker.unlock(fh)            
        info['JOB_IDX']=jobid    
        log.debug("added key ['JOBID'] to info object")
        
    def create_workdir(self,info,log):
        """
        Create a working directory.
        
        The location is stored in the info object with the key 'WORKDIR'.
        
        @type info: dict         
        @param info: Dictionary object with information needed by the class
        @type log: Logger 
        @param log: Logger to store log messages  
        """
        keys = ['BASEDIR','JOB_IDX','PARAM_IDX','FILE_IDX','NAME']
        if not info.has_key(keys[0]):
            log.error('info object does not contain key [%s]' % keys[0])
            log.error('no work dir has been created')            
        if not info.has_key(keys[1]):
            self._set_jobid(info,log)               
        path_items = []    
        for k in keys:
            if info.has_key(k):
                path_items.append(info[k])
        # join need a list of strings.
        # the list has to be parsed explicitly because list might contain integers       
        path = (os.path.sep).join(map( str, path_items ) ) 
        # creates the directory, if it exists, it's content is removed       
        FileUtils.makedirs_safe(log,path,clean=True)
        info['WORKDIR'] = path  
        log.debug("added key ['WORKDIR] to info object.")                         
                    
    def get_streams(self,info,log):
        """
        Initializes the streams for stdout/stderr/log.
        
        The type of the streams depends on the 'info' object.
        
        @precondition: 'info' object that has to contain the key 'STORAGE'
        @type info: dict         
        @param info: Dictionary object with information needed by the class
        @type log: Logger 
        @param log: Logger to store log messages  
        
        Return: Tuple of boolean, message that explains boolean,
        out_stream, err_stream, log_stream        
        """   
        
        storage = info['STORAGE']
        log.debug('STORAGE type: [%s]' % storage)
        if storage == 'memory':
            out_stream = StringIO()            
            err_stream = StringIO() 
            log_stream = StringIO() 
            log.debug('Created in-memory streams')                                      
        elif storage == 'file':
            out_file = ''.join([info['NAME'],".out"])
            err_file = ''.join([info['NAME'],".err"]) 
            log_file = ''.join([info['NAME'],".log"])                      
            created_files = [out_file,err_file,log_file]
            info['CREATED_FILES'] = created_files
            log.debug("add [%s] to info['CREATED_FILES'] to copy them later to the work directory")            
            # streams are initialized with 'w+' that files newly created and therefore previous versions are deleted.
            out_stream = open(out_file, 'w+')            
            err_stream = open(err_file, 'w+')  
            log_stream = open(log_file,'w+')
            log.debug('Created file-based streams')                                 
        else:                        
            log.fatal('Exit program because storage type is not supported.')
            sys.exit(1)
        return (out_stream,err_stream,log_stream)  
    
    
    def reset_streams(self):
        """
        Reset the stdout/stderr to their default
        """
        sys.stdout = sys.__stdout__
        sys.stderr = sys.__stderr__                  
    
    def get_args_handler(self):
        """
        Define which command line argument handler to use
        
        @rtype: IArgsHandler
        @return: An implementation of the IArgsHandler interface. 
        """ 
    
    def get_info_handler(self):
        """
        Define which information handler to use
        
        @rtype: IInformation
        @return: An implementation of the IInformation interface. 
        """     
    
    def run_app(self,info,log,app):
        """
        Executes an object that implements the supported Application interface.        
        
        @type info: dict         
        @param info: Dictionary object with information needed by the class
        @type log: Logger 
        @param log: Logger to store log messages  
        @type app: 
        @param app: Object that implements a supported interface from the interface module  
        
        @rtype: (int,dict)
        @return: Tuple of 2 objects; the exit code and the (updated) info object.
        """
        raise NotImplementedError("run() is not implemented.")                                                                                                                                           
                                                                        

class ApplicationRunner(Runner):
    """    
    Runner class that supports application that implement the IApplication interface.
    """
    
    def get_args_handler(self):
        """
        See super class
        """

        return ApplicationArgsHandler() 

    def get_info_handler(self):  
        """
        Information from the command line and the input file(s) are merged with priority to the
        command line information.
        Output is only written to a single file
        """
        
        return BasicInformationHandler()                  
    
    def run_app(self,app,info,log):
        """
        Run a python application
        
        See super class.
        """        
        if isinstance(app,IApplication):
            return app.main(info,log)
        else:                                    
            self.log.critical('the object [%s] is not an instance of one of the following %s'% 
                              (app.__class__.__name__,
                               [IApplication,__class__.__name__]))  
            return (1,info)
        
        

class WrapperRunner(ApplicationRunner):
    """
    Runner class that supports application that implement the IWrapper interface      
        
    The Application type is used to create workflow nodes that 
    prepare, run and validate the execution of an external application.
    """
    
    def _run(self,command,storage):
        """
        Execute a command and collects it's output in self.out_stream and self.err_stream.
         
        The stdout and stderr are written to files if file system should be used.
        Otherwise stdout and stderr of the application are separately printed to 
        stdout because the logger uses by default the stderr.
        
        @type command: string
        @param command: Command that will be executed
        @type storage: string
        @param storage: Storage type for the out/err streams produced by the command line execution  
        
        @rtype: int
        @return: Return code. It is either 1 or the original return code of the executed command.        
        """
        # when the command does not exist, process just dies.therefore a try/catch is needed          
        try:     
            if storage == 'memory':
                p = Popen(command, shell=True, stdout=PIPE, stderr=PIPE)            
                output, error = p.communicate()                                                                                                                                                                            
                self.out_stream = StringIO(output)
                self.err_stream = StringIO(error)  
            elif storage == 'file':
                p = Popen(command, shell=True,stdout=sys.stdout, stderr=sys.stderr)
                p.wait()
            else:
                self.log.critical('storage type [%s] is not supported' % 
                                  self.info['storage'])
                return 1                       
            return p.returncode                       
        except Exception,e:
            self.log.exception(e)
            return 1       
        
    def get_args_handler(self):
        """
        See super class
        """

        return WrapperArgsHandler()                     
    
    def run_app(self,app,info,log):
        """
        Prepare, run and validate the execution of an external program. 
        
        See super class.
        """
        if isinstance(app,IWrapper):
            log.info('Start [%s]' % app.prepare_run.__name__)
            command,info = app.prepare_run(info,log)     
            log.info('Finish [%s]' % app.prepare_run.__name__)
            if command is None:
                log.critical('Command was [None]. Interface of [%s] is possibly not correctly implemented' %
                                  app.__class__.__name__)
                return (1,info)                
            # necessary when e.g. the template file contains '\n' what will cause problems 
            # when using concatenated shell commands
            log.debug('remove all [\\n] from command string')
            command  = command.replace('\n','')   
            log.info('Command [%s]' % str(command))
            log.info('Start [%s]' % self._run.__name__)
            run_code = self._run(command,info['STORAGE'])
            log.info('Finish [%s]' % self._run.__name__)
            log.info('run_code [%s]' % run_code)        
            log.info('Start [%s]' % app.validate_run.__name__)
            # set stream pointer the start that in validate can use 
            # them immediately with .read() to get content
            self.out_stream.seek(0)
            self.err_stream.seek(0)
            exit_code,info = app.validate_run(info,log,run_code,self.out_stream,self.err_stream)
            log.debug('exit code [%s]' % exit_code)
            log.info('Finish [%s]' % app.validate_run.__name__)        
            return (exit_code,info)
        else:                                    
            self.log.critical('the object [%s] is not an instance of one of the following %s'% 
                              (app.__class__.__name__,
                               [IApplication,__class__.__name__]))  
            return (1,info)             