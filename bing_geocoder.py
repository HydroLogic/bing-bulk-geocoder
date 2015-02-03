import json
import logging
import os
import pytz
import requests
import StringIO
import time

from csv import DictReader
from datetime import datetime, timedelta

LOGGER = logging.getLogger(__name__)


class BingGeocoder:
    """
    Class to handle uploading/checking on/downloading addresses for geocoding.
    """

    def __init__(self, key):
        self.key = key

    def upload_addresses(self, addresses):
        """
        Given list of dicts of {'address', 'entity_id'}, send them to Bing for processing.
        """
        url = ('http://spatial.virtualearth.net/REST/v1/Dataflows/Geocode?input=csv&key=%s' %
               self.key)
        header_preamble = 'Bing Spatial Data Services, 2.0'
        header_fields = [
            'Id',
            'GeocodeRequest/Culture',
            'GeocodeRequest/ConfidenceFilter/MinimumConfidence',
            'GeocodeRequest/Query',
            'GeocodeResponse/Point/Latitude',
            'GeocodeResponse/Point/Longitude'
        ]
        header = '%s\n%s' % (header_preamble, ', '.join(header_fields))
        body = []
        line_format = '%s,en-US,High,%s,,'
        for address in addresses:
            body.append(line_format % (address['entity_id'], address['address']))
        data = "%s\n%s" % (header, '\n'.join(body))
        LOGGER.debug('Uploading %d addresses for geocoding' % len(body))
        try:
            r = requests.post(url, data=data, headers={"Content-Type": "text/plain"})
        except Exception, e:
            LOGGER.exception('Error uploading addresses: %s' % e)

    def get_job_statuses(self, min_cutoff=1440):
        """
        Connect to Bing API and get list of all available jobs. Only return jobs completed after
        min_cutoff minutes ago; default is 24 hours' worth. Set to 0 to return all jobs.
        """
        url = ('http://spatial.virtualearth.net/REST/v1/dataflows/listjobs?key=%s' % self.key)
        now = datetime.now(pytz.UTC)
        delta = timedelta(minutes=min_cutoff)
        result_links = []
        r = requests.get(url)
        for rs in r.json()['resourceSets']:
            for resource in rs['resources']:
                if 'completedDate' not in resource:
                    continue
                completed = datetime.strptime(
                    resource['completedDate'],
                    '%a, %d %b %Y %H:%M:%S %Z')
                if min_cutoff == 0 or completed.replace(tzinfo=pytz.UTC) > now - delta:
                    for link in resource['links']:
                        if 'name' in link and link['name'] == 'succeeded':
                            result_links.append(link['url'])
        return result_links

    def get_job_results(self, include_jobs):
        """
        Connect to Bing API and get results of geocode jobs. If include_jobs is given, just return
        results for those job ids. Return list of (entity_id, address, lat, lng) tuples for each job
        id.
        """
        result_links = get_job_statuses()
        result_rows = []
        for link in result_links:
            if not include_jobs or link in include_jobs:
                url = '%s?key=%s' % (link, settings.BING_MAPS_KEY)
                r = requests.get(url, headers={"Content-Type": "text/plain"})
                if len(r.text.splitlines()) > 2:
                    result_data = StringIO.StringIO()
                    for line in r.text.splitlines()[1:]:
                        result_data.writeline(line)
                    reader = DictReader(result_data)
                    for line in reader:
                        result_rows.append(line)
        return result_rows


def main():
    env_var = 'BING_MAPS_API_KEY'
    if env_var in os.environ:
        geocoder = BingGeocoder(os.environ[env_var])
    else:
        key = raw_input('Enter Bing Maps API key: ')
        if key:
            geocoder = BingGeocoder(key)
        else:
            print 'Error: Need to enter Bing Maps API key.'
            return
    print geocoder.get_job_statuses(0)

if __name__ == '__main__':
    main()


"""
class Command(BaseCommand):
    help = "Geocodes any points that haven't been geocoded already."

    def handle(self, *args, **options):
        save_results_to_db()
        LOGGER.info(
            'Currently %d missing points' % PersonEntity.objects.filter(point=None).count())
        begin = 0
        end = 30000
        seen = set()
        while end < 300000:
            # Our quota limit is 50 requests over 24 hours or 10 simultaneous jobs
            LOGGER.info('Getting a new set, between %d and %d' % (begin, end))
            people = PersonEntity.objects.filter(point=None)[begin:end]
            addresses = []
            for person in people:
                address = create_address(
                    person.address_1,
                    person.address_2,
                    person.city,
                    person.state,
                    person.zipcode).replace(',', ' ')
                if address not in seen:
                    seen.add(address)
                    addresses.append({
                        'address': address,
                        'entity_id': 'personentity_%s' % person.pk
                        })
            upload_addresses(addresses)
            begin = end
            end += 30000
"""
