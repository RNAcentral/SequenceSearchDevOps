"""
Copyright [2009-2017] EMBL-European Bioinformatics Institute
Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at
     http://www.apache.org/licenses/LICENSE-2.0
Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

import json
import logging
import os
import datetime

from aiohttp.test_utils import unittest_run_loop
from aiohttp.test_utils import AioHTTPTestCase
import sqlalchemy as sa

from ..main import create_app
from ..models import Job, JobChunk, JobChunkResult, Consumer
from ..consumers import free_consumer, find_available_consumers, find_highest_priority_job_chunk, \
    save_job_chunk_started, save_job_chunk_error, delegate_job_to_consumer


class FindAvailableConsumersTestCase(AioHTTPTestCase):
    """
    Run this test with the following command:

    ENVIRONMENT=TEST python3 -m unittest producer.tests.test_consumers.FindAvailableConsumersTestCase

    """
    async def get_application(self):
        logging.basicConfig(level=logging.ERROR)  # subdue messages like 'DEBUG:asyncio:Using selector: KqueueSelector'
        app = create_app()
        return app

    async def setUpAsync(self):
        await super().setUpAsync()

        async with self.app['engine'].acquire() as connection:
            await connection.execute(
                Consumer.insert().values(
                    ip='192.168.0.2',
                    status='available'
                )
            )

            await connection.execute(
                Consumer.insert().values(
                    ip='192.168.0.3',
                    status='busy'
                )
            )

            await connection.execute(
                Consumer.insert().values(
                    ip='192.168.0.4',
                    status='available'
                )
            )

    async def tearDownAsync(self):
        async with self.app['engine'].acquire() as connection:
            await connection.execute('DELETE FROM job_chunk_results')
            await connection.execute('DELETE FROM job_chunks')
            await connection.execute('DELETE FROM jobs')
            await connection.execute('DELETE FROM consumer')

            await super().tearDownAsync()

    @unittest_run_loop
    async def test_find_available_consumer(self):
        consumers = await find_available_consumers(self.app['engine'])

        for index, row in enumerate(consumers):
            if index == 0:
                assert row.ip == '192.168.0.2'
                assert row.status == 'available'
            elif index == 1:
                assert row.ip == '192.168.0.4'
                assert row.status == 'available'


class FreeConsumersTestCase(AioHTTPTestCase):
    """
    Run this test with the following command:

    ENVIRONMENT=TEST python3 -m unittest producer.tests.test_consumers.FreeConsumersTestCase
    """
    async def get_application(self):
        logging.basicConfig(level=logging.ERROR)  # subdue messages like 'DEBUG:asyncio:Using selector: KqueueSelector'
        app = create_app()
        return app

    async def setUpAsync(self):
        await super().setUpAsync()

        async with self.app['engine'].acquire() as connection:
            self.consumer = await connection.scalar(
                Consumer.insert().values(
                    ip='192.168.0.2',
                    status='busy'
                )
            )

            self.job_id = await connection.scalar(
                Job.insert().values(query='AACAGCATGAGTGCGCTGGATGCTG', submitted=datetime.datetime.now(), status='started')
            )

            self.job_chunk_id1 = await connection.scalar(
                JobChunk.insert().values(
                    job_id=self.job_id,
                    database='mirbase',
                    submitted=datetime.datetime.now(),
                    status='started',
                    consumer=self.consumer
                )
            )

    async def tearDownAsync(self):
        async with self.app['engine'].acquire() as connection:
            await connection.execute('DELETE FROM job_chunk_results')
            await connection.execute('DELETE FROM job_chunks')
            await connection.execute('DELETE FROM jobs')
            await connection.execute('DELETE FROM consumer')

            await super().tearDownAsync()

    @unittest_run_loop
    async def test_free_consumer(self):
        await free_consumer(self.app['engine'], '192.168.0.2')

        async with self.app['engine'].acquire() as connection:
            self.consumer = await connection.execute('''
              SELECT id, ip, status
              FROM consumer
              WHERE ip='192.168.0.2'
            ''')

            for row in self.consumer:
                assert row.status == 'available'


class HighestPriorityJobChunkConsumerTestCase(AioHTTPTestCase):
    """
    Run this test with the following command:

    ENVIRONMENT=TEST python3 -m unittest producer.tests.test_consumers.HighestPriorityJobChunkConsumerTestCase
    """
    async def get_application(self):
        logging.basicConfig(level=logging.ERROR)  # subdue messages like 'DEBUG:asyncio:Using selector: KqueueSelector'
        app = create_app()
        return app

    async def setUpAsync(self):
        await super().setUpAsync()

        async with self.app['engine'].acquire() as connection:
            self.job_id = await connection.scalar(
                Job.insert().values(query='AACAGCATGAGTGCGCTGGATGCTG', submitted=datetime.datetime.now(), status='started')
            )

            self.job_id2 = await connection.scalar(
                Job.insert().values(query='CGTGCTGAATAGCTGGAGAGGCTCAT', submitted=datetime.datetime.now(), status='started')
            )

            self.job_chunk_id1 = await connection.scalar(
                JobChunk.insert().values(
                    job_id=self.job_id,
                    database='mirbase',
                    submitted=datetime.datetime.now(),
                    status='started'
                )
            )

            self.job_chunk_id2 = await connection.scalar(
                JobChunk.insert().values(
                    job_id=self.job_id2,
                    database='pombase',
                    submitted=datetime.datetime.now(),
                    status='started'
                )
            )

    async def tearDownAsync(self):
        async with self.app['engine'].acquire() as connection:
            await connection.execute('DELETE FROM job_chunk_results')
            await connection.execute('DELETE FROM job_chunks')
            await connection.execute('DELETE FROM jobs')

            await super().tearDownAsync()

    @unittest_run_loop
    async def test_find_highest_priority_job_chunk(self):
        job_chunk_id = await find_highest_priority_job_chunk(self.app['engine'])

        assert job_chunk_id == self.job_chunk_id1


class SaveJobChunkStartedConsumerTestCase(AioHTTPTestCase):
    """
    Run this test with the following command:

    ENVIRONMENT=TEST python3 -m unittest producer.tests.test_consumers.SaveJobChunkStartedConsumerTestCase
    """
    async def get_application(self):
        logging.basicConfig(level=logging.ERROR)  # subdue messages like 'DEBUG:asyncio:Using selector: KqueueSelector'
        app = create_app()
        return app

    async def setUpAsync(self):
        await super().setUpAsync()

        async with self.app['engine'].acquire() as connection:
            self.job_id = await connection.scalar(
                Job.insert().values(query='AACAGCATGAGTGCGCTGGATGCTG', submitted=datetime.datetime.now(), status='started')
            )

    @unittest_run_loop
    async def test_job_chunk_started(self):
        await save_job_chunk_started(self.app['engine'], job_id, database, reason)


class SaveJobChunkErrorConsumerTestCase(AioHTTPTestCase):
    """
    Run this test with the following command:

    ENVIRONMENT=TEST python3 -m unittest producer.tests.test_consumers.SaveJobChunkErrorConsumerTestCase
    """
    async def get_application(self):
        logging.basicConfig(level=logging.ERROR)  # subdue messages like 'DEBUG:asyncio:Using selector: KqueueSelector'
        app = create_app()
        return app

    async def setUpAsync(self):
        await super().setUpAsync()

        async with self.app['engine'].acquire() as connection:
            self.job_id = await connection.scalar(
                Job.insert().values(query='AACAGCATGAGTGCGCTGGATGCTG', submitted=datetime.datetime.now(), status='started')
            )

    @unittest_run_loop
    async def test_except_error_in_job_chunk(self):
        await save_job_chunk_error(self.app['engine'], job_id, database, reason)


class DelegateJobToConsumerConsumerTestCase(AioHTTPTestCase):
    """
    Run this test with the following command:

    ENVIRONMENT=TEST python3 -m unittest producer.tests.test_consumers.DelegateJobToConsumerConsumerTestCase
    """
    async def get_application(self):
        logging.basicConfig(level=logging.ERROR)  # subdue messages like 'DEBUG:asyncio:Using selector: KqueueSelector'
        app = create_app()
        return app

    async def setUpAsync(self):
        await super().setUpAsync()

        async with self.app['engine'].acquire() as connection:
            self.job_id = await connection.scalar(
                Job.insert().values(query='AACAGCATGAGTGCGCTGGATGCTG', submitted=datetime.datetime.now(), status='started')
            )

    @unittest_run_loop
    async def test_delegate_job_to_consumer(self):
        pass
