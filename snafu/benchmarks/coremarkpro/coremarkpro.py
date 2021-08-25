#/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Runs CoreMark Pro."""
from datetime import datetime
import pprint
import shlex
import uuid
from typing import Any, Dict, Iterable, List, Optional, Tuple, Union
from snafu.config import ConfigArgument
from snafu.benchmarks import Benchmark, BenchmarkResult
from snafu.process import sample_process, ProcessSample
import subprocess
import os
import re


class Coremarkpro(Benchmark):
    """ Wrapper for CoreMark Pro"""

    """ Set for Benchmark Class """
    tool_name = "coremark-pro"
    args = (
            ConfigArgument(
                "-p",
                "--path",
                dest="path",
                type=str,
                help="Path to the coremark-pro's directory",
                required=True,
                ),
            ConfigArgument(
                "-c",
                "--context",
                dest="context",
                type=int,
                help="CoreMark Pro's context",
                required=False,
                ),
            ConfigArgument(
                "-w",
                "--workloads",
                help="CoreMark Pro's workloads",
                dest="workload",
                type=int,
                required=False,
                ),
            ConfigArgument(
                "-s",
                "--sample",
                dest="sample",
                env_var="SAMPLE",
                default=1,
                type=int,
                help="Number of times to run the benchmark",
                required=False,
                ),
            ConfigArgument(
                "-u",
                "--upload",
                dest="upload",
                default=False,
                type=bool,
                help="Parse results from previous CoreMark Run",
                required=False,
                ),
            )


    """ Helper functions"""

    def build_workload_cmd(self):
        xcmd = ""
        if getattr(self.config, "context"):
            xcmd += f" -c{self.config.context}"
        if getattr(self.config, "workload"):
            xcmd += f" -w{self.config.workload} "
        return shlex.split(f"make TARGET=linux64 certify-all XCMD='{xcmd}'")

    def parse_raw_logs(self):
        headers = ['uid', 'suite', 'name', 'ctx', 'wrk', 'fails', 't(s)', 'iter', 'iter/s', 'codesize', 'datasize']
        types = [str, str, str, int, int, int, float, int, float, int, int]

        with open(self.config.path + 'builds/linux64/gcc64/logs/linux64.gcc64.log', 'rt') as file:
            results = []
            run_type = ""
            run_starttime = ""
            for line in file:
                result = re.search(r'^#Results for (\w+) .* (\d+:\d+:\d+:\d+) XCMD', line)
                if result:
                    (run_type, run_starttime) = result.group(1,2)
                    continue
                if 'median' not in line:
                    #result = re.search(r'^#Results for (\w+) .* (\d+:\d+:\d+:\d+) XCMD', line)
                    #result = re.search(r'^#Results for (\w+) .* (\d+:\d+:\d+:\d+) XCMD', line)
                    if re.search(r'^\d+', line):
                        cols = re.split(r'\s+', line.rstrip())
                        converted_cols = [func(val) for func, val in zip(types, cols)]
                        record = dict(zip(headers, converted_cols))
                        record['type'] = run_type
                        record['starttime'] = self.convert_coremark_timestamp(run_starttime)
                        results.append(record)

            return results

    def parse_marks(self):
        headers = ['name',  'multicore', 'singlecore', 'scaling']
        types = [str, float, float, float]
        test_results = []
        with open(self.config.path + 'builds/linux64/gcc64/logs/linux64.gcc64.mark', 'rt') as file:
            table_name = ""
            results = {}
            for line in file:
                line = line.rstrip()
                if not line:
                    continue

                # Find where the table starts and skips the fluff
                if "RESULTS TABLE" in line:
                    table_name = line.split(' ')[0].lower()
                    while True:
                        # Exit out of loop once it finds the table delimiter
                        if('---' in next(file)):
                            break
                    continue

                cols = re.split(r'\s+', line.rstrip())
                converted_cols = [func(val) for func, val in zip(types, cols)]
                record = dict(zip(headers, converted_cols))
                record['type'] = table_name
                test_results.append(record)

        return test_results

    def submit_results(self, sample_starttime) -> BenchmarkResult:

        test_config = {
                "workload": self.config.workload,
                "context": self.config.context,
                }
        result_summary = {
                #"clustername": self.config.cluster_name,
                "date": sample_starttime,
                "sample": self.config.sample,
                "test_config": test_config,
                }

        test_results = {
                "summary_results": self.parse_marks(),
                "raw_results": self.parse_raw_logs()
                }

        return self.create_new_result(
                data=test_results,
                config=result_summary,
                tag="results",
                )

    def convert_coremark_timestamp(self, timestamp):
        from dateutil import tz
        time_obj = datetime.strptime(timestamp, '%y%j:%H:%M:%S')
        utc_tz = tz.gettz('UTC')

        return (time_obj.astimezone(utc_tz)).strftime("%Y-%m-%dT%H:%M:%S.%fZ")   


    """ Override member functions from Benchmark class"""

    def setup(self) -> bool:

        # Parse the command line args
        self.config.parse_args()

        # Sets up defaults for the required variables
        self.config.uuid = os.getenv("uuid", str(uuid.uuid4()))
        self.config.user = os.getenv("test_user", "myuser")
        if "clustername" not in os.environ:
            self.config.cluster_name = "mycluster"

        return True

    def collect(self) -> Iterable[BenchmarkResult]:

        cmd = self.build_workload_cmd()

        if not self.config.upload:
            for sample_num in range(1, self.config.sample + 1):
                self.logger.info(f"Starting coremark-pro sample number {sample_num}")

                sample_starttime = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%fZ")

                # Runs the actual command
                sample: ProcessSample = sample_process(
                        cmd, self.logger, retries=2, expected_rc=0,  cwd=self.config.path
                        )

                if not sample.success:
                    self.logger.critical(f"Failed to run! Got results: {sample}")
                    return
                else:
                    yield self.submit_results(sample_starttime)
        else:
            sample_starttime = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%fZ")
            yield self.submit_results(sample_starttime)


    def cleanup(self):
        return True
