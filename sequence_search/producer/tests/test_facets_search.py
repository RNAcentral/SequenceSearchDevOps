"""
Copyright [2009-2019] EMBL-European Bioinformatics Institute
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

import datetime
import logging
import uuid

from aiohttp.test_utils import unittest_run_loop
from aiohttp.test_utils import AioHTTPTestCase

from sequence_search.db.models import Job, JobChunk, JobChunkResult, JOB_STATUS_CHOICES, JOB_CHUNK_STATUS_CHOICES
from sequence_search.db.settings import get_postgres_credentials
from sequence_search.producer.__main__ import create_app


"""
Run these tests with:

ENVIRONMENT=TEST python3 -m unittest sequence_search.producer.tests.test_facets_search
"""


class EBISearchProxyTestCase(AioHTTPTestCase):
    async def get_application(self):
        logging.basicConfig(level=logging.ERROR)  # subdue messages like 'DEBUG:asyncio:Using selector: KqueueSelector'
        app = create_app()
        settings = get_postgres_credentials(ENVIRONMENT='TEST')
        app.update(name='test', settings=settings)
        return app

    async def setUpAsync(self):
        await super().setUpAsync()
        self.job_id = str(uuid.uuid4())

        async with self.app['engine'].acquire() as connection:
            await connection.execute(
                Job.insert().values(
                    id=self.job_id,
                    query='',
                    submitted=datetime.datetime.now(),
                    status=JOB_STATUS_CHOICES.started
                )
            )

            self.job_chunk_id1 = await connection.scalar(
                JobChunk.insert().values(
                    job_id=self.job_id,
                    database='mirbase',
                    submitted=datetime.datetime.now(),
                    status=JOB_CHUNK_STATUS_CHOICES.started
                )
            )
            await connection.execute(
                JobChunk.insert().values(
                    job_id=self.job_id,
                    database='pombase',
                    submitted=datetime.datetime.now(),
                    status=JOB_CHUNK_STATUS_CHOICES.started
                )
            )

            await connection.scalar(
                JobChunkResult.insert().values(
                    job_chunk_id=self.job_chunk_id1,
                    rnacentral_id='URS000075D2D2_10090',
                    description='Mus musculus miR - 1195 stem - loop',
                    score=6.5,
                    bias=0.7,
                    e_value=32,
                    target_length=98,
                    alignment="Query  8 GAGUUUGAGACCAGCCUGGCCA 29\n| | | | | | | | | | | | | | | | | |\nSbjct_10090\n22\nGAGUUCGAGGCCAGCCUGCUCA\n43",
                    alignment_length=22,
                    gap_count=0,
                    match_count=18,
                    nts_count1=22,
                    nts_count2=0,
                    identity=81.81818181818183,
                    query_coverage=73.33333333333333,
                    target_coverage=0,
                    gaps=0,
                    query_length=30,
                    result_id=1
                )
            )

            await connection.scalar(
                JobChunkResult.insert().values(
                    job_chunk_id=self.job_chunk_id1,
                    rnacentral_id='URS000004F5D8_10090',
                    description='Mus musculus miR - 1195 stem - loop',
                    score=6.5,
                    bias=0.7,
                    e_value=32,
                    target_length=98,
                    alignment="Query  8 GAGUUUGAGACCAGCCUGGCCA 29\n| | | | | | | | | | | | | | | | | |\nSbjct_10090\n22\nGAGUUCGAGGCCAGCCUGCUCA\n43",
                    alignment_length=22,
                    gap_count=0,
                    match_count=18,
                    nts_count1=22,
                    nts_count2=0,
                    identity=81.81818181818183,
                    query_coverage=73.33333333333333,
                    target_coverage=0,
                    gaps=0,
                    query_length=30,
                    result_id=1
                )
            )

    async def tearDownAsync(self):
        async with self.app['engine'].acquire() as connection:
            await connection.execute('DELETE FROM job_chunk_results')
            await connection.execute('DELETE FROM job_chunks')
            await connection.execute('DELETE FROM infernal_result')
            await connection.execute('DELETE FROM infernal_job')
            await connection.execute('DELETE FROM jobs')

        await super().tearDownAsync()

    @unittest_run_loop
    async def test_job_status_success(self):
        url = self.app.router["facets-search"].url_for(job_id=str(self.job_id))
        async with self.client.get(path=url) as response:
            assert response.status == 200
