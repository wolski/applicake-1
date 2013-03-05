#!/bin/env python

'''
Created on Nov 11, 2010

@author: quandtan
'''

import os
import shutil
import sys
import time, random
from cStringIO import StringIO
from subprocess import Popen
from subprocess import PIPE
from applicake.framework.argshandler import ArgsHandler
from applicake.framework.enums import KeyEnum
from applicake.framework.logger import Logger
from applicake.framework.interfaces import IApplication
from applicake.framework.interfaces import IWrapper
from applicake.framework.informationhandler import BasicInformationHandler
from applicake.utils.fileutils import FileUtils
from applicake.utils.fileutils import FileLocker
from applicake.utils.dictutils import DictUtils                          
from applicake.utils.stringutils import StringUtils
                 
                 
class Runner(KeyEnum):
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
        # default values
        default_info = {
                        self.NAME: app.__class__.__name__,                        
                        self.STORAGE:'memory',
                        self.LOG_LEVEL:'DEBUG',
                        self.COPY_TO_WD: [],  
                        self.PRINT_LOG: True      
                        } 
        #set default values
        info = default_info        
        tmp_log_stream = StringIO()
        exit_code = 1
        # needed e.g. in collector
        self.app = app
        try:
            # create memory logger            
            log = Logger.create(level=default_info[self.LOG_LEVEL],name=StringUtils.get_random(15),stream=tmp_log_stream)
            log.debug('created temporary in-memory logger')
#            # get command line arguments
#            args = sys.argv
            log.debug('application class file [%s]' % args[0])
            log.debug('arguments [%s]' % args[1:])
            log.debug('Runner class [%s]' % self.__class__.__name__)
            log.debug('Application class [%s]' % app.__class__.__name__)
            log.info('Start [%s]' % self.get_args_handler.__name__)
            args_handler = self.get_args_handler()
            log.info('Start [%s]' % app.set_args.__name__)   
            args_handler = app.set_args(log,args_handler)
            log.info('Start [%s]' % args_handler.get_parsed_arguments.__name__)
            try:
                pargs = args_handler.get_parsed_arguments(log,args)
            except:
                # need to reset streams in order to allow args_handler to print usage message
                self.reset_streams() 
                return exit_code
            log.info('Start [%s]' % self.get_info_handler.__name__)
            info_handler = self.get_info_handler()
            log.info('Start [%s]' % info_handler.get_info.__name__)
            try:
                # overwrite previous default values
                info = info_handler.get_info(log, pargs)
            except Exception, e:
                # if get_info() fails, default info is set and the program stopped by
                # sys.exit(1) so the final dear_down can start
                info = default_info
                log.exception(e)
                sys.exit(1)
            log.info('initial content of info [%s]' % info)
            info = DictUtils.merge(log,info, default_info,priority='left')
            if isinstance(info[self.LOG_LEVEL],list):
                info[self.LOG_LEVEL] = info[self.LOG_LEVEL][0]
            log.debug('Setting to loglevel from info: %s',info[self.LOG_LEVEL])
            log.setLevel(info[self.LOG_LEVEL])
            log.debug('Added default values to info they were not set before')            
            log.debug('content of final info [%s]' % info)   
            log.info('Start [%s]' % self.create_workdir.__name__)
            info = self.create_workdir(info,log)              
            log.info('Start [%s]' % self.get_streams.__name__)               
            (self.out_stream,self.err_stream,self.log_stream) = self.get_streams(info,log)                
            sys.stdout = self.out_stream
            log.debug('set sys.out to new out stream')
            sys.stderr = self.err_stream
            log.debug('set sys.err to new err stream')
            log.debug('redirect sys streams for stdout/stderr depending on the chosen storage type')                      
            log = Logger.create(level=info[self.LOG_LEVEL],
                         name=info[self.NAME],stream=self.log_stream)      
            log.debug('created new logger dependent of the storage')
            tmp_log_stream.seek(0)
            self.log_stream.write(tmp_log_stream.read())
            log.debug('wrote content of temporary logger to new logger')                
            log.info('Start [%s]' % self.run_app.__name__)
            exit_code,info = self.run_app(app,info,log,args_handler)
            if exit_code != 0:
                log.fatal('exit code of run_app() != 0')
                if info[self.STORAGE] == 'memory_all':
                    print self.reset_streams()
                    print self.out_stream.read()
                    print self.err_stream.read()
                sys.exit(1)                             
            log.info('Start [%s]' % info_handler.write_info.__name__)
            info_handler.write_info(info,log)
            log.info('Start [%s]' % self._cleanup.__name__)
            exit_code,info,log = self._cleanup(info,log)
            log.debug('info [%s]' % info)
            log.debug('exit code [%s]' %exit_code)                 
        except Exception, e:
            log.fatal('error in __call__')
            log.exception(e) 
            self.reset_streams() 
        finally:
            log.info('Start [%s]' % self.reset_streams.__name__)
            self.reset_streams() 
            if hasattr(self, 'log_stream'): 
                stream = self.log_stream
            else:
                stream = tmp_log_stream               
            stream.seek(0)               
            if info[self.PRINT_LOG] or info[self.STORAGE]== 'memory_all':
                sys.stderr.write(stream.read())
            self.info = info  
            return exit_code
        
    def _cleanup(self,info,log):
        """
        Does the final clean-up
        
        - copies input files and output file to working dir
        - copies created files to working dir
        - If storage='memory' is used, out and err stream are printed to stdout
        - log stream is printed to stderr
        
        @type info: dict         
        @param info: Dictionary object with information needed by the class
        @type log: Logger 
        @param log: Logger to store log messages   
        
        @rtype: (int,dict,logger)
        @return: Tuple of 3 objects; the exit code,the (updated) info object and the updated logger.          
        """     
        try:    
            log.info('Start [%s]' % self.reset_streams.__name__)
            self.reset_streams()
            log.info('Finished [%s]' % self.reset_streams.__name__)
            log.debug('found key [%s] [%s]' % (self.WORKDIR, info.has_key(self.WORKDIR)))        
            if info.has_key(self.WORKDIR):
                wd = info[self.WORKDIR]
                log.debug('start copying/moving files to work dir')
                # copy input files to working directory
                files_to_copy = []
                if info.has_key(self.INPUT) and len(info[self.INPUT]) >0 :
                    log.debug('check for input files to copy')
                    log.debug('found following input files to copy [%s]' % info[self.INPUT])
                    DictUtils.get_flatten_sequence(log,[files_to_copy,info[self.INPUT]])
                    files_to_copy.extend(info[self.INPUT])
                if info.has_key(self.OUTPUT) and len(info[self.OUTPUT]) >0:
                    log.debug('check for output files to copy')
                    DictUtils.get_flatten_sequence(log,[files_to_copy,info[self.OUTPUT]])
                    log.debug('found following output file to copy [%s]' % info[self.OUTPUT])
                    files_to_copy.append(info[self.OUTPUT])            
                for path in files_to_copy:
                    # 'r' escapes special characters
                    src = r'%s' % os.path.abspath(path) 
                    try:
                        shutil.copy(src,wd) 
                        log.debug('Copied [%s] to [%s]' % (src,wd))
                    except:
                        log.critical('Counld not copy [%s] to [%s]' % (src,wd))
                        return (1,info,log)            
            if info[self.STORAGE] == 'memory':
                print '=== stdout ==='
                self.out_stream.seek(0)
                for line in self.out_stream.readlines():
                    print line
                print '=== stderr ==='
                self.err_stream.seek(0)
                for line in self.err_stream.readlines():
                    print line                 
            if info[self.STORAGE] == 'memory_all':
                print '=== stdout ==='
                self.out_stream.seek(0)
                for line in self.out_stream.readlines():
                    print line
                print '=== stderr ==='
                self.err_stream.seek(0)
                for line in self.err_stream.readlines():
                    print line 
                #print of log done in finally of __call__
                #sys.stderr.write('==log==\n')
                #self.log_stream.seek(0)
                #for line in self.log_stream.readlines():
                #    sys.stderr.write(line)                                    
            # move created files to working directory
            # 'created_files might be none e.g. if memory-storage is used   
            if info.has_key(self.COPY_TO_WD) and info[self.COPY_TO_WD] != []:  
                for path in info[self.COPY_TO_WD]:
                    # check if element is a key of info and not an actual file
                    if info.has_key(path):
                        path = info[path]
                        src = r'%s' % os.path.abspath(path) 
                        dest = r'%s' % os.path.join(wd,os.path.basename(path))
                        info[path] = dest
                        log.debug('set value of key [%s] from [%s] to [%s]' % (path,info[path],dest))
                    else:
                        src = r'%s' % os.path.abspath(path) 
                        dest = r'%s' % os.path.join(wd,os.path.basename(path))                    
                    try:
                        shutil.copy(src,wd)
                        log.debug('Copy [%s] to [%s]' % (src,dest))
                    except:
                        if FileUtils.is_valid_file(log, dest):
                            log.debug('file [%s] already exists' % dest)
                        else:
                            log.fatal('Stop program because could not copy [%s] to [%s]' % (src,dest))
                            return(1,info,log)
            return (0,info,log)
        except Exception, e:
            log.critical(e)
            return 1,info,log           
                    
    def _set_jobid(self,info,log):
        """
        Creates job id by taking current time & adding random numbers (to avoid overlap)
        the job id is used for creating the workdir (@see create_workdir)
        
        @type info: dict         
        @param info: Dictionary object with information needed by the class
        @type log: Logger 
        @param log: Logger to store log messages  
        """
        if not info.has_key(self.BASEDIR):
            log.warn("info has not key [%s]. " % self.BASEDIR +
                     "Therefore the key [%s] is not set" % (self.JOB_IDX))                       
        else:    
            info[self.JOB_IDX]= time.strftime('%Y%m%d_%H%M%S_') + str( random.randint(100000,999999) )
            log.info("added JOB_IDX = %s to info object" % info[self.JOB_IDX])
        
    def create_workdir(self,info,log):
        """
        Create a working directory.
        
        The location is stored in the info object with the key [%s].
        
        @type info: dict         
        @param info: Dictionary object with information needed by the class
        @type log: Logger 
        @param log: Logger to store log messages  
        
        @rtype info: dict         
        @return info: Dictionary object with the (updated) information needed by the class        
        """ % self.WORKDIR
        
        keys = [self.BASEDIR,self.JOB_IDX,self.PARAM_IDX,self.FILE_IDX,self.NAME]
        if not info.has_key(keys[0]):
            log.info('info object does not contain key [%s], use current dir [%s] instead' % (keys[0],os.getcwd()))      
        if not info.has_key(keys[1]):
            log.debug('BEFORE JOBID ADDED: [%s]' % info)
            self._set_jobid(info,log)  
            log.debug('AFTER JOBID ADDED: [%s]' % info)             
        path_items = []    
        for k in keys:
            if info.has_key(k):
                path_items.append(info[k])
        # join need a list of strings.
        # the list has to be parsed explicitly because list might contain integers       
        path = (os.path.sep).join(map( str, path_items ) ) 
        # creates the directory, if it exists, it's content is removed       
        FileUtils.makedirs_safe(log,path,clean=True)
        info[self.WORKDIR] = path  
        log.debug("added key [%s] to info object." % self.WORKDIR)    
        return info                     
                    
    def get_streams(self,info,log):
        """
        Initializes the streams for stdout/stderr/log.
        
        The type of the streams depends on the 'info' object.
        
        @precondition: 'info' object that has to contain the keys [%s,%s]
        @type info: dict         
        @param info: Dictionary object with information needed by the class
        @type log: Logger 
        @param log: Logger to store log messages  
        
        Return: Tuple of boolean, message that explains boolean,
        out_stream, err_stream, log_stream        
        """ % (self.STORAGE,self.NAME)      
        required_keys = [self.STORAGE,self.NAME]
        for key in required_keys:
            log.debug('found key [%s]: [%s]' % (key, info.has_key(key)))
        storage = info[self.STORAGE]
        log.debug('STORAGE type: [%s]' % storage)
        if storage == 'memory' or storage == 'memory_all':
            out_stream = StringIO()            
            err_stream = StringIO() 
            log_stream = StringIO() 
            log.debug('Created in-memory streams')                                      
        elif storage == 'file':
            base = info[self.NAME]
            if info.has_key(self.WORKDIR):
                base = os.path.join(info[self.WORKDIR],base)             
            out_file = ''.join([base,".out"])
            err_file = ''.join([base,".err"]) 
            log_file = ''.join([base,".log"])                      
#            created_files = [out_file,err_file,log_file]
#            info[self.COPY_TO_WD] = created_files
#            log.debug("add [%s] to info['%s'] to copy them later to the work directory" % (created_files,self.COPY_TO_WD))            
            # streams are initialized with 'w+' that files newly created and therefore previous versions are deleted.
            out_stream = open(out_file, 'w+',buffering=0)            
            err_stream = open(err_file, 'w+',buffering=0)  
            log_stream = open(log_file,'w+',buffering=0)
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
        raise NotImplementedError("get_args_handler() is not implemented.")
    
    def get_info_handler(self):
        """
        Define which information handler to use
        
        @rtype: IInformation
        @return: An implementation of the IInformation interface. 
        """     
        raise NotImplementedError("get_info_handler() is not implemented.")
    
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
        return ArgsHandler()

    def get_info_handler(self):  
        """
        Information from the command line and the input file(s) are merged with priority to the
        command line information.
        Output is only written to a single file
        """       
        return BasicInformationHandler()                  
    
    def run_app(self,app,info,log,args_handler):
        """
        Run a python application
        
        See super class.
        """  
        exit_code = None     
        if isinstance(app,IApplication):
            log.info('get subset of info based on following keys [%s]' % args_handler.get_app_argnames())
            app_info = DictUtils.extract(info, args_handler.get_app_argnames())
            log.debug('app_info [%s]' % app_info)
            exit_code,app_info = app.main(app_info,log)   
            log.debug('content of app_info after running app [%s]' % app_info)  
            log.debug('content of info [%s]' % info)  
            info = DictUtils.merge(log,info, app_info,priority='right')    
            log.debug('content of info after merge with app_info [%s]' % info)
        else:                                    
            log.critical('the object [%s] is not an instance of one of the following %s'% 
                              (app.__class__.__name__,
                               IApplication().__class__.__name__))  
            exit_code = 1
        return exit_code,info
    

class IniFileRunner(ApplicationRunner):
    """
    Specific runner for applications that need access to the complete content of the info object.
    """

    def run_app(self,app,info,log,args_handler):
        """
        See super class.
        
        Generators require access to the complete info object, not only to specific informations.
        """  
        exit_code = None     
        if isinstance(app,IApplication):
            exit_code,info = app.main(info,log)   
        else:                                    
            self.log.critical('the object [%s] is not an instance of one of the following %s'% 
                              (app.__class__.__name__,
                               [IApplication,__class__.__name__]))  
            exit_code = 1
        return exit_code,info  
    
class IniFileRunner2(IniFileRunner):
    """
    Like IniFileRunner but for application that run directly after a collector.
    
    Adaptations of the info object have to be made if an app (such as a generator) runs after a collector app.
    """

    def create_workdir(self,info,log):
        """
        See super class.
        """  
        if info.has_key(self.WORKDIR):
            del info[self.WORKDIR]     
        check_keys = [self.PARAM_IDX,self.FILE_IDX]
        mod_info = info.copy()
        for key in check_keys:            
            log.debug('check key :%s'% key)
            if isinstance(mod_info[key],list):
                log.debug('found list as value. Therefore key is not considered for creating the work dir.')
                del mod_info[key]            
        mod_info = super(IniFileRunner2,self).create_workdir(mod_info,log)
        return DictUtils.merge(log,info, mod_info, priority='left')
    
    
class CollectorRunner(ApplicationRunner):             
    """
    Specific runner for collector applications.
    """
    
    def _add_additional_info(self,info,log):
            '''
            Need to extract specific information from the first collector file if no input file is defined.
            '''
            pargs = {}
            collector_file = self.app.get_collector_files(info, log)[0] 
            log.debug('collector file taken to extract additional infos [%s]' % collector_file)
            pargs[self.INPUT] = [collector_file]
            collector_info = self.get_info_handler().get_info(log, pargs)
            log.debug('info from collector file [%s]' % collector_info)
            # the info is needed to create the work directory
            keys = [self.BASEDIR,self.JOB_IDX,self.LOG_LEVEL,self.STORAGE]            
            needed_info = DictUtils.extract(collector_info, keys, include=True)
            return DictUtils.merge(log,info, needed_info, priority='right')       
    
    def create_workdir(self,info,log):
        """
        """
        if not info.has_key(self.INPUT):
            # need to extract information about workdir if no input file is given
            log.info('did not find [%s] key. Get additional information from first collector file. ' % self.INPUT)            
            info = self._add_additional_info(info, log)
            log.info('info with additional information [%s]' % info)
        return super(CollectorRunner,self).create_workdir(info,log)

    def run_app(self,app,info,log,args_handler):
        """
        Collectors require a different merging between the (default) information and the information from the collector files.
        
        See super class.
        """  
        exit_code = None     
        if isinstance(app,IApplication):
            log.info('get subset of info based on following keys [%s]' % args_handler.get_app_argnames())
            app_info = DictUtils.extract(info, args_handler.get_app_argnames())
            log.debug('app_info [%s]' % app_info)
            exit_code,app_info = app.main(app_info,log)   
            log.debug('content of app_info after running app [%s]' % app_info)  
            log.debug('content of info [%s]' % info) 
            
#            # takes basedir and job_idx from the app_info
#            bd = app_info[self.BASEDIR]
#            if isinstance(bd, list):
#                bd = bd[0]
#            info[self.BASEDIR] = bd
#            idx = app_info[self.JOB_IDX]
#            if isinstance(idx, list):
#                idx = idx[0]
#            info[self.JOB_IDX] = idx                
#            # takes new info and reset workdir
#            new_wd = os.path.join(bd,idx,info[self.NAME])
#            old_wd = info[self.WORKDIR]
#            log.debug('%s,%s' % (old_wd,new_wd))
##            log.debug('files in old wd [%s]' % os.listdir(old_wd))   
##            log.debug('files in new wd [%s]' % os.listdir(new_wd))
#            shutil.copytree(old_wd, new_wd, symlinks=False, ignore=None)
#            info[self.WORKDIR] = new_wd
            info = DictUtils.merge(log,info, app_info,priority='left')  
            
            # !!!  TODO add collector files to key 'CREATED_FILES' in order to copy them to the workdir !!!
              
            log.debug('content of info after merge with app_info [%s]' % info)
        else:                                    
            self.log.critical('the object [%s] is not an instance of one of the following %s'% 
                              (app.__class__.__name__,
                               [IApplication,__class__.__name__]))  
            exit_code = 1
        return exit_code,info   
        
class EngineCollectorRunner(CollectorRunner):
    def run_app(self,app,info,log,args_handler):
        if isinstance(app,IApplication):
            return app.main(info,log)   
        else:                                    
            log.critical('given app is not iApplication')  
            return 1, info
    
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
            if storage == 'memory' or storage == 'memory_all':
                p = Popen(command, shell=True, stdout=PIPE, stderr=PIPE)            
                output, error = p.communicate()                                                                                                                                                                            
                self.out_stream = StringIO(output)
                self.err_stream = StringIO(error)  
            elif storage == 'file':
                p = Popen(command, shell=True,stdout=sys.stdout, stderr=sys.stderr)
                p.wait()
            else:
                self.log.critical('storage type [%s] is not supported' % 
                                  self.info[self.STORAGE])
                return 1                       
            return p.returncode                       
        except Exception,e:
            self.log.exception(e)
            return 1                          
    
    def run_app(self,app,info,log,args_handler):
        """
        Prepare, run and validate the execution of an external program. 
        
        See super class.
        """
        exit_code = None
        if isinstance(app,IWrapper):
            
            log.info('get subset of info based on following keys [%s]' % args_handler.get_app_argnames())
            app_info = DictUtils.extract(info, args_handler.get_app_argnames())
            log.debug('app_info [%s]' % app_info)
            log.info('Start [%s]' % app.prepare_run.__name__)
            command,app_info = app.prepare_run(app_info,log)                 
            log.info('Finish [%s]' % app.prepare_run.__name__)
            log.debug('content of app_info [%s]' % app_info)    
            info = DictUtils.merge(log,info, app_info,priority='right')    
            log.debug('content of info after merge with app_info [%s]' % info)             
            if command is None:
                log.critical('Command was [None]. Interface of [%s] is possibly not correctly implemented' %
                                  app.__class__.__name__)
                exit_code = 1
            else:    
                # necessary when e.g. the template file contains '\n' what will cause problems 
                # when using concatenated shell commands
                log.debug('remove all [\\n] from command string')
                command  = command.replace('\n','')   
                log.info('Command [%s]' % str(command))             
                log.info('Start [%s]' % self._run.__name__)
                run_code = self._run(command,info[self.STORAGE])
                log.info('Finish [%s]' % self._run.__name__)
                log.info('run_code [%s]' % run_code)        
                log.info('Start [%s]' % app.validate_run.__name__)
                # set stream pointer the start that in validate can use 
                # them immediately with .read() to get content
                self.out_stream.seek(0)
                self.err_stream.seek(0)
                log.info('get subset of info based on following keys [%s]' % args_handler.get_app_argnames())
                app_info = DictUtils.extract(info, args_handler.get_app_argnames())
                log.debug('app_info [%s]' % app_info)               
                exit_code,app_info = app.validate_run(app_info,log,run_code,self.out_stream,self.err_stream)
                log.debug('exit code [%s]' % exit_code)
                log.debug('content of app_info [%s]' % app_info)                        
                log.info('Finish [%s]' % app.validate_run.__name__) 
                info = DictUtils.merge(log,info, app_info,priority='right')    
                log.debug('content of info after merge with app_info [%s]' % info) 
        else:                                   
            log.critical("the object [%s] is not an instance of one of the following [%s]" % (app.__class__.__name__ ,
                                                                                                 IWrapper.__class__.__name__))  
            exit_code = 1
        return exit_code,info
    
class WrapperRunnerSubfile(WrapperRunner):
    """
    Like WrapperRunner but for application that uses SUBFILE_IDX
    """

    def create_workdir(self,info,log):        
        keys = [self.BASEDIR,self.JOB_IDX,self.PARAM_IDX,self.FILE_IDX,'SUBFILE_IDX',self.NAME]
        path_items = []    
        for k in keys:
            if info.has_key(k):
                path_items.append(info[k])
            #if one of the keys is missing then exception is thrown. good.
        
        # join need a list of strings.
        # the list has to be parsed explicitly because list might contain integers       
        path = (os.path.sep).join(map( str, path_items ) ) 
        # creates the directory, if it exists, it's content is removed       
        FileUtils.makedirs_safe(log,path,clean=True)
        info[self.WORKDIR] = path  
        log.debug("added key [%s] to info object." % self.WORKDIR)    
        return info  

class ApplicationRunnerSubfile(ApplicationRunner):
    def create_workdir(self,info,log):        
        keys = [self.BASEDIR,self.JOB_IDX,self.PARAM_IDX,self.FILE_IDX,'SUBFILE_IDX',self.NAME]
        path_items = []    
        for k in keys:
            if info.has_key(k):
                path_items.append(info[k])
            #if one of the keys is missing then exception is thrown. good.
        
        # join need a list of strings.
        # the list has to be parsed explicitly because list might contain integers       
        path = (os.path.sep).join(map( str, path_items ) ) 
        # creates the directory, if it exists, it's content is removed       
        FileUtils.makedirs_safe(log,path,clean=True)
        info[self.WORKDIR] = path  
        log.debug("added key [%s] to info object." % self.WORKDIR)    
        return info 
