'''
Created on Jun 11, 2012

@author: quandtan
'''

import os
from applicake.applications.proteomics.base import OpenMs
from applicake.framework.templatehandler import BasicTemplateHandler

class FeatureFinderCentroided(OpenMs):
    """
    Wrapper for the OpenMS tools FeatureFinderCentroided.
    """

    _input_file = ''
    _result_file = ''

    def __init__(self):
        """
        Constructor
        """
        base = self.__class__.__name__
        self._input_file = '%s.ini' % base # application specific config file
        self._result_file = '%s.featureXML' % base # result produced by the application

    def _get_prefix(self,info,log):
        if not info.has_key(self.PREFIX):
            info[self.PREFIX] = 'FeatureFinderCentroided'
            log.debug('set [%s] to [%s] because it was not set before.' % (self.PREFIX,info[self.PREFIX]))
        return info[self.PREFIX],info

    def get_template_handler(self):
        """
        See interface
        """
        return FeatureFinderCentroidedTemplate()

    def prepare_run(self,info,log):
        """
        See interface.

        - Read the a specific template and replaces variables from the info object.
        - Tool is executed using the pattern: [PREFIX] -ini [TEMPLATE].
        - If there is a result file, it is added with a specific key to the info object.
        """
        wd = info[self.WORKDIR]
        log.debug('reset path of application files from current dir to work dir [%s]' % wd)
        self._input_file = os.path.join(wd,self._input_file)
        info['TEMPLATE'] = self._input_file
        self._result_file = os.path.join(wd,self._result_file)
        info['FEATUREXML'] = self._result_file
        log.debug('get template handler')
        th = self.get_template_handler()
        log.debug('modify template')
        mod_template,info = th.modify_template(info, log)
        prefix,info = self._get_prefix(info,log)
        command = '%s -ini %s' % (prefix,self._input_file)
        return command,info

    def set_args(self,log,args_handler):
        """
        See interface
        """
        args_handler = super(FeatureFinderCentroided, self).set_args(log,args_handler)
        args_handler.add_app_args(log, 'MZML', 'The input mzML file ')
        args_handler.add_app_args(log, 'FEATUREXML', 'The output featureXML file ')
        return args_handler
    
class StrictLfq(FeatureFinderCentroided): 
    
    def get_template_handler(self):
        """
        See interface
        """
        return StrictLfqTemplate()     


class FeatureFinderCentroidedTemplate(BasicTemplateHandler):
    """
    Template handler for FeatureFinderCentroided.
    """

    def read_template(self, info, log):
        """
        See super class.
        """
        template = """<?xml version="1.0" encoding="ISO-8859-1"?>
<PARAMETERS version="1.3" xsi:noNamespaceSchemaLocation="http://open-ms.sourceforge.net/schemas/Param_1_3.xsd" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <NODE name="FeatureFinderCentroided" description="Detects two-dimensional features in LC-MS data.">
    <ITEM name="version" value="1.9.0" type="string" description="Version of the tool that generated this parameters file." tags="advanced" />
    <NODE name="1" description="Instance &apos;1&apos; section for &apos;FeatureFinderCentroided&apos;">
      <ITEM name="in" value="$MZML" type="string" description="input file" tags="input file,required" restrictions="*.mzML" />
      <ITEM name="out" value="$FEATUREXML" type="string" description="output file" tags="output file,required" restrictions="*.featureXML" />
      <ITEM name="seeds" value="" type="string" description="User specified seed list" tags="input file" restrictions="*.featureXML" />
      <ITEM name="log" value="" type="string" description="Name of log file (created only when specified)" tags="advanced" />
      <ITEM name="debug" value="0" type="int" description="Sets the debug level" tags="advanced" />
      <ITEM name="threads" value="$THREADS" type="int" description="Sets the number of threads allowed to be used by the TOPP tool" />
      <ITEM name="no_progress" value="false" type="string" description="Disables progress logging to command line" tags="advanced" restrictions="true,false" />
      <ITEM name="test" value="false" type="string" description="Enables the test mode (needed for internal use only)" tags="advanced" restrictions="true,false" />
      <NODE name="algorithm" description="Algorithm section">
        <ITEM name="debug" value="false" type="string" description="When debug mode is activated, several files with intermediate results are written to the folder &apos;debug&apos; (do not use in parallel mode)." restrictions="true,false" />
        <NODE name="intensity" description="Settings for the calculation of a score indicating if a peak&apos;s intensity is significant in the local environment (between 0 and 1)">
          <ITEM name="bins" value="10" type="int" description="Number of bins per dimension (RT and m/z). The higher this value, the more local the intensity significance score is.#br#This parameter should be decreased, if the algorithm is used on small regions of a map." restrictions="1:" />
        </NODE>
        <NODE name="mass_trace" description="Settings for the calculation of a score indicating if a peak is part of a mass trace (between 0 and 1).">
          <ITEM name="mz_tolerance" value="0.01" type="float" description="Tolerated m/z deviation of peaks belonging to the same mass trace.#br#It should be larger than the m/z resolution of the instument.#br#This value must be smaller than that 1/charge_high!" restrictions="0:" />
          <ITEM name="min_spectra" value="8" type="int" description="Number of spectra that have to show a similar peak mass in a mass trace." restrictions="1:" />
          <ITEM name="max_missing" value="2" type="int" description="Number of consecutive spectra where a high mass deviation or missing peak is acceptable.#br#This parameter should be well below &apos;min_spectra&apos;!" restrictions="0:" />
          <ITEM name="slope_bound" value="1" type="float" description="The maximum slope of mass trace intensities when extending from the highest peak.#br#This parameter is important to seperate overlapping elution peaks.#br#It should be increased if feature elution profiles fluctuate a lot." restrictions="0:" />
        </NODE>
        <NODE name="isotopic_pattern" description="Settings for the calculation of a score indicating if a peak is part of a isotoipic pattern (between 0 and 1).">
          <ITEM name="charge_low" value="2" type="int" description="Lowest charge to search for." restrictions="1:" />
          <ITEM name="charge_high" value="4" type="int" description="Highest charge to search for." restrictions="1:" />
          <ITEM name="mz_tolerance" value="0.01" type="float" description="Tolerated m/z deviation from the theoretical isotopic pattern.#br#It should be larger than the m/z resolution of the instument.#br#This value must be smaller than that 1/charge_high!" restrictions="0:" />
          <ITEM name="intensity_percentage" value="10" type="float" description="Isotopic peaks that contribute more than this percentage to the overall isotope pattern intensity must be present." tags="advanced" restrictions="0:100" />
          <ITEM name="intensity_percentage_optional" value="0.1" type="float" description="Isotopic peaks that contribute more than this percentage to the overall isotope pattern intensity can be missing." tags="advanced" restrictions="0:100" />
          <ITEM name="optional_fit_improvement" value="2" type="float" description="Minimal percental improvement of isotope fit to allow leaving out an optional peak." tags="advanced" restrictions="0:100" />
          <ITEM name="mass_window_width" value="25" type="float" description="Window width in Dalton for precalculation of estimated isotope distribtions." tags="advanced" restrictions="1:200" />
        </NODE>
        <NODE name="seed" description="Settings that determine which peaks are considered a seed">
          <ITEM name="min_score" value="0.5" type="float" description="Minimum seed score a peak has to reach to be used as seed.#br#The seed score is the geometric mean of intensity score, mass trace score and isotope pattern score.#br#If your features show a large deviation from the averagene isotope distribution or from an gaussian elution profile, lower this score." restrictions="0:1" />
        </NODE>
        <NODE name="fit" description="Settings for the model fitting">
          <ITEM name="epsilon_abs" value="0.0001" type="float" description="Absolute epsilon used for convergence of the fit." tags="advanced" restrictions="0:" />
          <ITEM name="epsilon_rel" value="0.0001" type="float" description="Relative epsilon used for convergence of the fit." tags="advanced" restrictions="0:" />
          <ITEM name="max_iterations" value="500" type="int" description="Maximum number of iterations of the fit." tags="advanced" restrictions="1:" />
        </NODE>
        <NODE name="feature" description="Settings for the features (intensity, quality assessment, ...)">
          <ITEM name="min_score" value="0.5" type="float" description="Feature score threshold for a feature to be reported.#br#The feature score is the geometric mean of the average relative deviation and the correlation between the model and the observed peaks." restrictions="0:1" />
          <ITEM name="min_isotope_fit" value="0.8" type="float" description="Minimum isotope fit of the feature before model fitting." tags="advanced" restrictions="0:1" />
          <ITEM name="min_trace_score" value="0.5" type="float" description="Trace score threshold.#br#Traces below this threshold are removed after the model fitting.#br#This parameter is important for features that overlap in m/z dimension." tags="advanced" restrictions="0:1" />
          <ITEM name="min_rt_span" value="0.333" type="float" description="Minimum RT span in relation to extended area that has to remain after model fitting." tags="advanced" restrictions="0:1" />
          <ITEM name="max_rt_span" value="2.5" type="float" description="Maximum RT span in relation to extended area that the model is allowed to have." tags="advanced" restrictions="0.5:" />
          <ITEM name="rt_shape" value="symmetric" type="string" description="Choose model used for RT profile fitting. If set to symmetric a gauss shape is used, in case of asymmetric an EGH shape is used." tags="advanced" restrictions="symmetric,asymmetric" />
          <ITEM name="max_intersection" value="0.35" type="float" description="Maximum allowed intersection of features." tags="advanced" restrictions="0:1" />
          <ITEM name="reported_mz" value="monoisotopic" type="string" description="The mass type that is reported for features.#br#&apos;maximum&apos; returns the m/z value of the highest mass trace.#br#&apos;average&apos; returns the intensity-weighted average m/z value of all contained peaks.#br#&apos;monoisotopic&apos; returns the monoisotopic m/z value derived from the fitted isotope model." restrictions="maximum,average,monoisotopic" />
        </NODE>
        <NODE name="user-seed" description="Settings for user-specified seeds.">
          <ITEM name="rt_tolerance" value="30" type="float" description="Allowed RT deviation of seeds from the user-specified seed position." restrictions="0:" />
          <ITEM name="mz_tolerance" value="0.1" type="float" description="Allowed m/z deviation of seeds from the user-specified seed position." restrictions="0:" />
          <ITEM name="min_score" value="0.5" type="float" description="Overwrites &apos;seed:min_score&apos; for user-specified seeds. The cutoff is typically a bit lower in this case." restrictions="0:1" />
        </NODE>
        <NODE name="debug" description="">
          <ITEM name="pseudo_rt_shift" value="500" type="float" description="Pseudo RT shift used when ." tags="advanced" restrictions="1:" />
        </NODE>
      </NODE>
    </NODE>
  </NODE>
</PARAMETERS>
"""
        log.debug('read template from [%s]' % self.__class__.__name__)
        return template,info


class StrictLfqTemplate(BasicTemplateHandler):
    """
    Template handler for FeatureFinderCentroided.
    """

    def read_template(self, info, log):
        """
        See super class.
        """
        template = """<?xml version="1.0" encoding="ISO-8859-1"?>
<PARAMETERS version="1.3" xsi:noNamespaceSchemaLocation="http://open-ms.sourceforge.net/schemas/Param_1_3.xsd" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <NODE name="FeatureFinderCentroided" description="Detects two-dimensional features in LC-MS data.">
    <ITEM name="version" value="1.9.0" type="string" description="Version of the tool that generated this parameters file." tags="advanced" />
    <NODE name="1" description="Instance &apos;1&apos; section for &apos;FeatureFinderCentroided&apos;">
      <ITEM name="in" value="$MZML" type="string" description="input file" tags="input file,required" restrictions="*.mzML" />
      <ITEM name="out" value="$FEATUREXML" type="string" description="output file" tags="output file,required" restrictions="*.featureXML" />
      <ITEM name="seeds" value="" type="string" description="User specified seed list" tags="input file" restrictions="*.featureXML" />
      <ITEM name="log" value="" type="string" description="Name of log file (created only when specified)" tags="advanced" />
      <ITEM name="debug" value="0" type="int" description="Sets the debug level" tags="advanced" />
      <ITEM name="threads" value="$THREADS" type="int" description="Sets the number of threads allowed to be used by the TOPP tool" />
      <ITEM name="no_progress" value="false" type="string" description="Disables progress logging to command line" tags="advanced" restrictions="true,false" />
      <ITEM name="test" value="false" type="string" description="Enables the test mode (needed for internal use only)" tags="advanced" restrictions="true,false" />
      <NODE name="algorithm" description="Algorithm section">
        <ITEM name="debug" value="false" type="string" description="When debug mode is activated, several files with intermediate results are written to the folder &apos;debug&apos; (do not use in parallel mode)." restrictions="true,false" />
        <NODE name="intensity" description="Settings for the calculation of a score indicating if a peak&apos;s intensity is significant in the local environment (between 0 and 1)">
          <ITEM name="bins" value="10" type="int" description="Number of bins per dimension (RT and m/z). The higher this value, the more local the intensity significance score is.#br#This parameter should be decreased, if the algorithm is used on small regions of a map." restrictions="1:" />
        </NODE>
        <NODE name="mass_trace" description="Settings for the calculation of a score indicating if a peak is part of a mass trace (between 0 and 1).">
          <ITEM name="mz_tolerance" value="0.01" type="float" description="Tolerated m/z deviation of peaks belonging to the same mass trace.#br#It should be larger than the m/z resolution of the instument.#br#This value must be smaller than that 1/charge_high!" restrictions="0:" />
          <ITEM name="min_spectra" value="8" type="int" description="Number of spectra that have to show a similar peak mass in a mass trace." restrictions="1:" />
          <ITEM name="max_missing" value="2" type="int" description="Number of spectra where a high mass deviation or missing peak is acceptable.#br#This parameter should be well below &apos;min_spectra&apos;!" restrictions="0:" />
          <ITEM name="slope_bound" value="1" type="float" description="The maximum slope of mass trace intensities when extending from the highest peak.#br#This parameter is important to seperate overlapping elution peaks.#br#It should be increased if feature elution profiles fluctuate a lot." restrictions="0:" />
        </NODE>
        <NODE name="isotopic_pattern" description="Settings for the calculation of a score indicating if a peak is part of a isotoipic pattern (between 0 and 1).">
          <ITEM name="charge_low" value="2" type="int" description="Lowest charge to search for." restrictions="1:" />
          <ITEM name="charge_high" value="6" type="int" description="Highest charge to search for." restrictions="1:" />
          <ITEM name="mz_tolerance" value="0.01" type="float" description="Tolerated m/z deviation from the theoretical isotopic pattern.#br#It should be larger than the m/z resolution of the instument.#br#This value must be smaller than that 1/charge_high!" restrictions="0:" />
          <ITEM name="intensity_percentage" value="10" type="float" description="Isotopic peaks that contribute more than this percentage to the overall isotope pattern intensity must be present." tags="advanced" restrictions="0:100" />
          <ITEM name="intensity_percentage_optional" value="0.1" type="float" description="Isotopic peaks that contribute more than this percentage to the overall isotope pattern intensity can be missing." tags="advanced" restrictions="0:100" />
          <ITEM name="optional_fit_improvement" value="2" type="float" description="Minimal percental improvement of isotope fit to allow leaving out an optional peak." tags="advanced" restrictions="0:100" />
          <ITEM name="mass_window_width" value="25" type="float" description="Window width in Dalton for precalculation of estimated isotope distribtions." tags="advanced" restrictions="1:200" />
        </NODE>
        <NODE name="seed" description="Settings that determine which peaks are considered a seed">
          <ITEM name="min_score" value="0.5" type="float" description="Minimum seed score a peak has to reach to be used as seed.#br#The seed score is the geometric mean of intensity score, mass trace score and isotope pattern score.#br#If your features show a large deviation from the averagene isotope distribution or from an gaussian elution profile, lower this score." restrictions="0:1" />
        </NODE>
        <NODE name="fit" description="Settings for the model fitting">
          <ITEM name="epsilon_abs" value="0.0001" type="float" description="Absolute epsilon used for convergence of the fit." tags="advanced" restrictions="0:" />
          <ITEM name="epsilon_rel" value="0.0001" type="float" description="Relative epsilon used for convergence of the fit." tags="advanced" restrictions="0:" />
          <ITEM name="max_iterations" value="500" type="int" description="Maximum number of iterations of the fit." tags="advanced" restrictions="1:" />
        </NODE>
        <NODE name="feature" description="Settings for the features (intensity, quality assessment, ...)">
          <ITEM name="min_score" value="0.5" type="float" description="Feature score threshold for a feature to be reported.#br#The feature score is the geometric mean of the average relative deviation and the correlation between the model and the observed peaks." restrictions="0:1" />
          <ITEM name="min_isotope_fit" value="0.6" type="float" description="Minimum isotope fit of the feature before model fitting." tags="advanced" restrictions="0:1" />
          <ITEM name="min_trace_score" value="0.4" type="float" description="Trace score threshold.#br#Traces below this threshold are removed after the model fitting.#br#This parameter is important for features that overlap in m/z dimension." tags="advanced" restrictions="0:1" />
          <ITEM name="min_rt_span" value="0.333" type="float" description="Minimum RT span in relation to extended area that has to remain after model fitting." tags="advanced" restrictions="0:1" />
          <ITEM name="max_rt_span" value="2.5" type="float" description="Maximum RT span in relation to extended area that the model is allowed to have." tags="advanced" restrictions="0.5:" />
          <ITEM name="rt_shape" value="symmetric" type="string" description="Choose model used for RT profile fitting. If set to symmetric a gauss shape is used, in case of asymmetric an EGH shape is used." tags="advanced" restrictions="symmetric,asymmetric" />
          <ITEM name="max_intersection" value="0.35" type="float" description="Maximum allowed intersection of features." tags="advanced" restrictions="0:1" />
          <ITEM name="reported_mz" value="monoisotopic" type="string" description="The mass type that is reported for features.#br#&apos;maximum&apos; returns the m/z value of the highest mass trace.#br#&apos;average&apos; returns the intensity-weighted average m/z value of all contained peaks.#br#&apos;monoisotopic&apos; returns the monoisotopic m/z value derived from the fitted isotope model." restrictions="maximum,average,monoisotopic" />
        </NODE>
        <NODE name="user-seed" description="Settings for user-specified seeds.">
          <ITEM name="rt_tolerance" value="30" type="float" description="Allowed RT deviation of seeds from the user-specified seed position." restrictions="0:" />
          <ITEM name="mz_tolerance" value="0.1" type="float" description="Allowed m/z deviation of seeds from the user-specified seed position." restrictions="0:" />
          <ITEM name="min_score" value="0.5" type="float" description="Overwrites &apos;seed:min_score&apos; for user-specified seeds. The cutoff is typically a bit lower in this case." restrictions="0:1" />
        </NODE>
        <NODE name="debug" description="">
          <ITEM name="pseudo_rt_shift" value="500" type="float" description="Pseudo RT shift used when ." tags="advanced" restrictions="1:" />
        </NODE>
      </NODE>
    </NODE>
  </NODE>
</PARAMETERS>
"""
        log.debug('read template from [%s]' % self.__class__.__name__)
        return template,info