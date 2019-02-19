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

from aiohttp import web

from ...db.consumers import delegate_job_chunk_to_consumer, set_consumer_status
from ...db.job_chunks import find_highest_priority_job_chunk, set_job_chunk_status, get_consumer_ip_from_job_chunk
from ...db.jobs import check_job_chunks_status, set_job_status, get_job_query, job_exists


async def serialize(connection, request, data):
    """Expected data: {"job_id": job_id, "database": database, "result": ""}"""
    try:
        job_id = data['job_id']
        database = data['database']
    except (KeyError, TypeError, ValueError) as e:
        raise web.HTTPBadRequest(text='Bad input') from e

    if not await job_exists(request.app['engine'], job_id):
        raise web.HTTPBadRequest(text='Bad input')

    if data['database'].lower() not in request.app['settings'].RNACENTRAL_DATABASES:
        raise web.HTTPBadRequest(text="Database '%s' not in list of RNACentral databases" % data['database'])
    data['database'] = data['database'].lower()

    return data


async def job_done(request):
    """
    Saves a job chunk to the database. If this was the last chunk,
    aggregates the results from all job chunks into job.
    """
    data = await request.json()

    async with request.app['engine'].acquire() as connection:
        data = await serialize(connection, request, data)

        # update job_chunk status, get job_chunk_id
        job_chunk_id = await set_job_chunk_status(request.app['engine'], data['job_id'], data['database'], status='success')
        if job_chunk_id is None:
            raise web.HTTPBadRequest(text="Job chunk, you're trying to update, is non-existent")

        # get consumer_ip
        consumer_ip = await get_consumer_ip_from_job_chunk(request.app['engine'], job_chunk_id)

        # if the whole job's done, update its status
        all_job_chunks_success = await check_job_chunks_status(request.app['engine'], data['job_id'])
        if all_job_chunks_success:
            await set_job_status(request.app['engine'], data['job_id'], 'success')

        # if there are any pending jobs, try scheduling another job chunk for this consumer
        (job_id, job_chunk_id, database) = await find_highest_priority_job_chunk(request.app['engine'])
        if job_id is not None:
            query = await get_job_query(request.app['engine'], job_id)
            await delegate_job_chunk_to_consumer(request.app['engine'], consumer_ip, job_id, database, query)
        else:
            await set_consumer_status(request.app['engine'], consumer_ip, 'available')

        return web.HTTPOk()
