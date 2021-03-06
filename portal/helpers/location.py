# -*- coding: utf-8 -*-
# Code for Life
#
# Copyright (C) 2017, Ocado Innovation Limited
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# ADDITIONAL TERMS – Section 7 GNU General Public Licence
#
# This licence does not grant any right, title or interest in any “Ocado” logos,
# trade names or the trademark “Ocado” or any other trademarks or domain names
# owned by Ocado Innovation Limited or the Ocado group of companies or any other
# distinctive brand features of “Ocado” as may be secured from time to time. You
# must not distribute any modification of this program using the trademark
# “Ocado” or claim any affiliation or association with Ocado or its employees.
#
# You are not authorised to use the name Ocado (or any of its trade names) or
# the names of any author or contributor in advertising or for publicity purposes
# pertaining to the distribution of this program, without the prior written
# authorisation of Ocado.
#
# Any propagation, distribution or conveyance of this program must include this
# copyright notice and these terms. You must not misrepresent the origins of this
# program; modified versions of the program must be marked as such and not
# identified as the original program.
import requests
import exceptions

class RequestException(exceptions.Exception):
    pass

class ApiException(exceptions.Exception):
    pass

def is_GB(component):
    return 'country' in component['types'] and component['short_name'] == 'GB'

def extract_locality(components):
    town = None
    country = None

    for component in components:
        if 'locality' in component['types']:
            town = component['long_name']

        if 'postal_town' in component['types']:
            town = component['long_name']

        if 'country' in component['types']:
            country = component['short_name']
    
    return town, country

def extract_location_data(results):
    for result in results:
        town, country = extract_locality(result['address_components'])
        location = result['geometry']['location']
        return country, town, location['lat'], location['lng']

    return None, None, None, None

# Uses Google Maps API to lookup location data using postcode + country(ISO 3166-1 alpha-2)
# By using country, it can return a more accurate location as the same postcode may exist in multiple countries
# Coordinates of the country will be returned if postcode is invalid in that country
def lookup_coord(postcode, country):

    payload = {'address': postcode, 'components': 'country:' + country}

    return get_location_from_api(payload)

# Using the Google Map API, lookup country using postcode
def lookup_country(postcode):

    payload = {'components': 'postal_code:' + postcode}

    return get_location_from_api(payload)

# Takes in payload as argument and use it when calling API
# Catches any error and return an error message as first element in the tuple
# Coordinates of GB is used if country is not specified, otherwise default to original country and 0 for coordinates
# Return format is:
#     error, country, town, latitude, longitude
def get_location_from_api(payload):
    # default location is UK and the coordinates of UK
    default_country = 'GB'
    default_town = 0
    default_lat = 55.378051
    default_lng = -3.435973

    if 'country' in payload.get('components'):
        default_country = payload.get('components', 'GB').rpartition(':')[2]
        default_town = default_lat = default_lng = 0

    # Catch error when there is a problem connecting to external API
    try:
        res = requests.get('https://maps.googleapis.com/maps/api/geocode/json',
                           params=payload)

        # Make sure status_code is 200 before deserialising json
        if not res.status_code == requests.codes.ok:
            raise RequestException(res.reason)

        data = res.json()

        status = data.get('status', 'No status')
        results = data.get('results', [])

        if not (status == 'OK' and len(results) > 0):
            raise ApiException(status)

        country, town, lat, lng = extract_location_data(results)

        return None, country or default_country, town or default_town, lat or default_lat, lng or default_lng

    except requests.exceptions.RequestException:
        error = 'Connection error'

    except RequestException as e:
        error = 'Request error: %s' % e

    except exceptions.ValueError as e:
        error = 'Value error: %s' % e

    except ApiException as e:
        error = 'API error: %s' % e

    return error, default_country, default_town, default_lat, default_lng