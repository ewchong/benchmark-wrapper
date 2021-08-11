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

    tool_name = "coremark-pro"
    # headers = ['uid', 'suite', 'name', 'ctx', 'wrk', 'fails',
    #             't(s)', 'iter', 'iter/s', 'codesize', 'datasize']
    headers = ['name',  'multicore', 'singlecore', 'scaling']

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
  )

    def setup(self) -> bool:
        self.config.parse_args()
        self.config.uuid = os.getenv("uuid", str(uuid.uuid4()))
        self.config.user = os.getenv("test_user", "myuser")

        self.logger.debug(f"Got config: {vars(self.config)}")

        if not getattr(self.config, "user", False):
            self.logger.critical("Missing required metadata. Need both user and uuid to continue")
            return False

        return True
    
    def parse_logs(self):
        with open(self.config.path + 'builds/linux64/gcc64/logs/linux64.gcc64.log', 'rt') as file:
            results = {}
            select = ['suite', 'name', 'ctx', 'wrk', 'iter/s']
            indices = [self.headers.index(colname) for colname in select]
            print(select, indices)
            for line in file:
                result = re.search('median\s+(single|best)$', line)
                if result:
                    test_type = result.group(1)
                    print(test_type)
                    cols = re.split('\s+', line.rstrip())
                    record = dict(zip(self.headers, cols))
                    print(record)
                    results.setdefault(record['name'], {})[
                        test_type] = record['iter/s']
                    # test_type, name, contexts, workers, ips = cols[1], cols[2], cols[3], cols[4], cols[8]
                    # print(test_type, name, contexts, workers, ips)
                    # print(record)
                # if(cols[0] == 'Workload'):
                #  next()

            print(results)

    def collect(self) -> Iterable[BenchmarkResult]:
        """Run the Ping Test Benchmark and collect results."""
        print(self.config.path)
        cmd = shlex.split(f"make TARGET=linux64 certify-all")

        sample_starttime = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%fZ")

        sysbench_result_summary = {
            # "clustername": self.cluster_name,
            "date": sample_starttime,
            # "sample": self.sample,
            # "test_config": self.test_config,
        }
        sample: ProcessSample = sample_process(
        		cmd, self.logger, retries=2, expected_rc=0,  cwd=self.config.path
        )

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
                    results[table_name] = []
                    print(table_name, "found")
                    while True:
                        # Exit out of loop once it finds the table delimiter
                        if('---' in next(file)):
                            break
                    continue

                cols = re.split('\s+', line.rstrip())
                record = dict(zip(self.headers, cols))
                result: BenchmarkResult = self.create_new_result(
                    data=record,
                    config={'start_time': sample_starttime},
                    tag="results",
                )
                yield result
                results[table_name].append(record)
                print(record)
        print(results)

    def cleanup(self):
        return True
