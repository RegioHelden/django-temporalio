from temporalio.client import Client

from django_temporalio.conf import settings


async def init_client():
    """
    Connect to Temporal.io server and return a client instance.
    """
    return await Client.connect(**settings.CLIENT_CONFIG)
