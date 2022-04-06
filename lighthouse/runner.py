# this python file uses the following encoding utf-8

# Python Standard Library
import json
import os
import subprocess
import tempfile
from collections import namedtuple
from functools import reduce
from tqdm import tqdm

# Own
from .report import LighthouseReport


class LighthouseRunner(object):
    """
    Lightweight runner, wraps around lighthouse-cli and parses the result

    Attributes:
        report (LighthouseReport): object with simplified report
    """

    def __init__(self, url, preset='desktop', quiet=False,
                 additional_settings=None):
        """
        Args:
            url (str): url to test
            preset WARNING: If the --config-path flag is provided, this preset will be ignored.  [string] [choices: "perf", "experimental", "desktop"]
            quiet (bool, optional): should not output anything to stdout,
                default is True
            additional_settings (list, optional): list of additional params
        """

        _, self.report_path = tempfile.mkstemp(suffix='.json')
        self._run(url, preset, quiet, additional_settings)
        self.report = self._get_report()
        self._clean()

    def _run(self, url, preset, quiet, additional_settings=None):
        report_path = self.report_path

        additional_settings = additional_settings or []

        try:
            command = [
                'lighthouse',
                url,
                '--quiet' if quiet else '',
                '--chrome-flags="--max-wait-for-load=10000"',
                '--preset={0}'.format(preset),
                '--output=json',
                '--output-path={0}'.format(report_path),
            ]

            command = command + additional_settings
            subprocess.check_call(' '.join(command), shell=True)
        except subprocess.CalledProcessError as exc:
            msg = '''
                Command "{0}"
                returned an error code: {1},
                output: {2}
            '''.format(exc.cmd, exc.returncode, exc.output)
            raise RuntimeError(msg)

    def _get_report(self):
        with open(self.report_path, 'r', encoding="utf8") as fil:
            return LighthouseReport(json.loads(fil.read()))

    def _clean(self):
        try:
            os.remove(self.report_path)
        except:
            pass


class LighthouseRepeatRunner(object):
    def __init__(self, url, preset='desktop', quiet=True,
                 additional_settings=None, repeats=3):
        reports = []

        progress = tqdm(range(1, repeats + 1), desc='Repeating test')

        for i in progress:
            progress.set_description('Run {0}/{1}'.format(i, repeats))
            reports.append(LighthouseRunner(url, preset=preset,
                                            quiet=quiet,
                                            additional_settings=additional_settings).report)   # noqa: E501

        report = namedtuple('LighthouseAveragedReport', 'timings, score')
        self.report = report(
            timings=self._get_average([getattr(x, 'timings') for x in reports]),  # noqa: E501
            score=self._get_average([getattr(x, 'score') for x in reports])
        )

    def _get_average(self, obj_lst):
        ret = {}
        for key in obj_lst[0].keys():
            lst = [x.get(key) for x in obj_lst]
            ret[key] = reduce(lambda a, b: a + b, lst) / len(lst)
        return ret
