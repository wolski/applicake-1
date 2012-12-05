'''
Created on Dec 4, 2012

@author: lorenz
'''
from applicake.applications.os.gzip import Gzip


class gzipXml(Gzip):
    
    def set_args(self,log,args_handler):
        args_handler.add_app_args(log, 'FEATUREXML', 'featurexml to compress')
        return args_handler
    
    def prepare_run(self, info, log):
        info['COMPRESS'] = info['FEATUREXML']
        return super(gzipXml,self).prepare_run(info,log)
