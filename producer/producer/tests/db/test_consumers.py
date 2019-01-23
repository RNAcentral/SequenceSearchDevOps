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

from ...main import create_app
from ...models import Job, JobChunk, JobChunkResult, Consumer
from ...db.consumers import get_consumer_status, set_consumer_status, find_available_consumers, delegate_job_chunk_to_consumer
from ...db.job_chunks import find_highest_priority_job_chunk


class FindAvailableConsumersTestCase(AioHTTPTestCase):
    """
    Run this test with the following command:

    ENVIRONMENT=TEST python3 -m unittest producer.tests.db.test_consumers.FindAvailableConsumersTestCase

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


class GetConsumerStatusTestCase(AioHTTPTestCase):
    """
    Run this test with the following command:

    ENVIRONMENT=TEST python3 -m unittest producer.tests.db.test_consumers.GetConsumerStatusTestCase
    """
    async def get_application(self):
        logging.basicConfig(level=logging.ERROR)
        app = create_app()
        return app

    async def setUpAsync(self):
        await super().setUpAsync()

        async with self.app['engine'].acquire() as connection:
            self.consumer_ip = '192.168.1.1'
            Consumer.insert().values(
                ip=self.consumer_ip,
                status='available'
            )

    async def tearDownAsync(self):
        async with self.app['engine'].acquire() as connection:
            await connection.execute('DELETE FROM job_chunk_results')
            await connection.execute('DELETE FROM job_chunks')
            await connection.execute('DELETE FROM jobs')
            await connection.execute('DELETE FROM consumer')

            await super().tearDownAsync()

    async def test_get_consumer_status(self):
        consumer_status = await get_consumer_status(self.app['engine'], '192.168.0.2')
        assert consumer_status == 'available'


class SetConsumerStatusTestCase(AioHTTPTestCase):
    """
    Run this test with the following command:

    ENVIRONMENT=TEST python3 -m unittest producer.tests.db.test_consumers.SetConsumerStatusTestCase
    """
    async def get_application(self):
        logging.basicConfig(level=logging.ERROR)  # subdue messages like 'DEBUG:asyncio:Using selector: KqueueSelector'
        app = create_app()
        return app

    async def setUpAsync(self):
        await super().setUpAsync()

        async with self.app['engine'].acquire() as connection:
            self.consumer_ip = '192.168.1.1'
            await connection.execute(
                Consumer.insert().values(
                    ip=self.consumer_ip,
                    status='busy'
                )
            )

            self.job_id = await connection.scalar(
                Job.insert().values(query='AACAGCATGAGTGCGCTGGATGCTG', submitted=datetime.datetime.now(), status='started')
            )

            self.job_chunk_id = await connection.scalar(
                JobChunk.insert().values(
                    job_id=self.job_id,
                    database='mirbase',
                    submitted=datetime.datetime.now(),
                    status='started',
                    consumer=self.consumer_ip
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
    async def test_set_consumer_status(self):
        await set_consumer_status(self.app['engine'], '192.168.0.2', 'available')

        async with self.app['engine'].acquire() as connection:
            consumer_status = await get_consumer_status(self.app['engine'], self.consumer_ip)
            assert consumer_status == 'busy'


class DelegateJobChunkToConsumerTestCase(AioHTTPTestCase):
    """
    Run this test with the following command:

    ENVIRONMENT=TEST python3 -m unittest producer.tests.db.test_consumers.DelegateJobChunkToConsumerConsumerTestCase
    """
    async def get_application(self):
        logging.basicConfig(level=logging.ERROR)  # subdue messages like 'DEBUG:asyncio:Using selector: KqueueSelector'
        app = create_app()
        return app

    async def setUpAsync(self):
        await super().setUpAsync()

        async with self.app['engine'].acquire() as connection:
            self.consumer_ip = '192.168.1.1'
            await connection.execute(
                Consumer.insert().values(
                    ip=self.consumer_ip,
                    status='avaiable'
                )
            )

            self.job_id = await connection.scalar(
                Job.insert().values(query='AACAGCATGAGTGCGCTGGATGCTG', submitted=datetime.datetime.now(), status='started')
            )

            self.job_chunk_id = await connection.scalar(
                JobChunk.insert().values(
                    job_id=self.job_id,
                    database='mirbase',
                    submitted=datetime.datetime.now(),
                    status='started',
                    consumer=self.consumer_ip
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
    async def test_delegate_job_to_consumer(self):
        # await delegate_job_chunk_to_consumer(
        #     self.app['engine'],
        #     self.consumer_ip,
        #     self.job_id,
        #     'mirbase',
        #     'AACAGCATGAGTGCGCTGGATGCTG'
        # )
        #
        # assert get_consumer_status(self.app['engine'], self.consumer_ip) == 'busy'
        pass
