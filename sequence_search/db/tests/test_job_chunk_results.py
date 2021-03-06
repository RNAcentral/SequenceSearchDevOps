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
import uuid

from aiohttp.test_utils import unittest_run_loop
import sqlalchemy as sa

from sequence_search.db.models import Job, JobChunk, JOB_STATUS_CHOICES, JOB_CHUNK_STATUS_CHOICES
from sequence_search.db.job_chunk_results import set_job_chunk_results
from sequence_search.db.tests.test_base import DBTestCase


class SetJobChunkResultsTestCase(DBTestCase):
    """
    Run this test with the following command:

    ENVIRONMENT=TEST python3 -m unittest sequence_search.db.tests.test_job_chunk_results.SetJobChunkResultsTestCase
    """
    async def setUpAsync(self):
        await super().setUpAsync()

        async with self.app['engine'].acquire() as connection:
            self.job_id = str(uuid.uuid4())

            await connection.execute(
                Job.insert().values(
                    id=self.job_id,
                    query='AACAGCATGAGTGCGCTGGATGCTG',
                    submitted=datetime.datetime.now(),
                    status=JOB_STATUS_CHOICES.started
                )
            )

            self.job_chunk_id = await connection.scalar(
                JobChunk.insert().values(
                    job_id=self.job_id,
                    database='mirbase',
                    submitted=datetime.datetime.now(),
                    status=JOB_CHUNK_STATUS_CHOICES.pending
                )
            )

    @unittest_run_loop
    async def test_set_job_chunk_results(self):
        results = [{
            "rnacentral_id": 'URS000075D2D2',
            "description": 'Mus musculus miR - 1195 stem - loop',
            "score": 6.5,
            "bias": 0.7,
            "e_value": 32.0,
            "target_length": 98,
            "alignment": "Query  8 GAGUUUGAGACCAGCCUGGCCA 29\n| | | | | | | | | | | | | | | | | |\nSbjct_10090\n22\nGAGUUCGAGGCCAGCCUGCUCA\n43",
            "alignment_length": 22,
            "gap_count": 0,
            "match_count": 18,
            "nts_count1": 22,
            "nts_count2": 0,
            "identity": 81.8181818181818,  # conversion to float in DB trims some digits
            "query_coverage": 73.3333333333333,  # converstion to float in DB trims some digits
            "target_coverage": 0.0,
            "gaps": 0.0,
            "query_length": 30,
            "result_id": 1
        }]

        await set_job_chunk_results(self.app['engine'], self.job_id, database='mirbase', results=results)

        async with self.app['engine'].acquire() as connection:
            query = sa.text('''
                SELECT rnacentral_id, description
                FROM job_chunk_results
                WHERE job_chunk_id=:job_chunk_id
            ''')

            async for row in await connection.execute(query, job_chunk_id=self.job_chunk_id):
                assert row.rnacentral_id == 'URS000075D2D2'
                assert row.description == 'Mus musculus miR - 1195 stem - loop'
