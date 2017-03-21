from pyquery import PyQuery as pq
import requests
import time
import json
import re
import googlemaps
import pickle
import datetime

db_date_format = "%Y-%m-%d"
conflicts_base_url = 'https://en.wikipedia.org/wiki/Category:Conflicts_in_%d'
wiki_base_url = 'http://en.wikipedia.org'
gmaps = googlemaps.Client(key='AIzaSyAmQNNfFa9NRlZ-Cv2QtUVTStZM6MvMn3A')

def conflict_pages_from_year(year):
    conflict_year_url = conflicts_base_url % year
    req = requests.get(conflict_year_url, headers={
        'authority': 'en.wikipedia.org',
        'method': 'GET',
        'path': '/wiki/War_in_Afghanistan_(2001%E2%80%932014)',
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'accept-encoding': 'gzip, deflate, sdch, br',
        'accept-language': 'en-US,en;q=0.8',
        'cache-control': 'max-age=0',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/56.0.2924.87 Safari/537.36'
    })
    # print(req.text)

    d = pq(req.text)
    conflict_anchors = d('div#mw-pages div.mw-category a')
    ret = []
    for i in range(len(conflict_anchors)):
        ret.append(conflict_anchors.eq(i).attr('href'))
    # print(ret)
    return ret

def conflict_page_to_info(page_url):
    req = requests.get(page_url, headers={
        'authority': 'en.wikipedia.org',
        'method': 'GET',
        'path': '/wiki/War_in_Afghanistan_(2001%E2%80%932014)',
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'accept-encoding': 'gzip, deflate, sdch, br',
        'accept-language': 'en-US,en;q=0.8',
        'cache-control': 'max-age=0',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/56.0.2924.87 Safari/537.36'
    })
    # print(req.text)

    d = pq(req.text)
    page_title = d('title').text()
    print(page_title)
    b = d('table.vevent').eq(0);
    # trs = b.parents('tr').siblings('tr')
    trs = b.children('tr')
    ret = {
        'partof': [],
        'belligerents': [],
        'locations': [],
        'raw_date': None
    }
    headers = [
        'belligerents',
        'casualties and losses',
        'strength',
        'units involved',
        'commanders and leaders'
    ]

    header_tr_ranges = {}
    curr_header = None
    start_ind = None
    for i in range(len(trs)):
        dd = pq(trs.eq(i))
        th_lt = dd.text().strip().lower()
        if any(th_lt in h_i for h_i in headers):
            if curr_header is not None:
                # print('end:', curr_header)
                header_tr_ranges[curr_header] = (start_ind + 1, i)

            start_ind = i
            curr_header = th_lt
            # print('start:', curr_header)
        elif any(
            len(dd('th[colspan="' + str(x) + '"]')) > 0
            for x in range(2, 5)
        ):
            if curr_header is not None:
                # print('end:', curr_header)
                header_tr_ranges[curr_header] = (start_ind + 1, i)
                curr_header = None
                start_ind = None

    if curr_header is not None:
        # print('end:', curr_header)
        header_tr_ranges[curr_header] = (start_ind + 1, len(trs))

    print(header_tr_ranges)

    for i in range(len(trs)):
        dd = pq(trs.eq(i))
        # tr = trs.eq(i)
        td = dd('td')
        text = td.text()

        # print(text.strip().lower())
        # print(text.strip().lower().startswith('part of'))
        td_lt = text.strip().lower()
        th_lt = dd.text().strip().lower()
        # print(th_lt)
        if td_lt.startswith('part of'):
            # print(tr)
            partof_anchors = dd('a')
            for i in range(len(partof_anchors)):
                anchor = partof_anchors.eq(i)
                ret['partof'].append({
                    'href': anchor.attr('href'),
                    'title': anchor.attr('title'),
                    'text': anchor.text()
                })

    if 'belligerents' in header_tr_ranges:
        bel = header_tr_ranges['belligerents']
        sides = None
        for i in range(bel[0], bel[1]):
            tds = pq(trs.eq(i))('td')
            if sides is None:
                sides = []
                for r in range(len(tds)):
                    sides.append([])

            # print(len(tds))
            # print(sides)
            for j in range(len(tds)):
                td = tds.eq(j)
                anchors = pq(td)('a')
                for k in range(len(anchors)):
                    a = pq(anchors.eq(k))
                    # print(a.attr('class'))
                    if a.attr('class') == None and a.parents('sup') == [] and a.parents('li') == []:
                        if not a.attr('href') in (
                            x['href'] for x in sides[j]
                        ):
                            sides[j].append({
                                'href': a.attr('href'),
                                'title': a.attr('title'),
                                'text': a.text()    
                            })
        ret['belligerents'] = sides

    """
    (\d+(,\d+)*)\+? civilians killed
    civilians killed: (\d+(,\d+)*)\+?
    (\d+(,\d+)*)\+? killed
    total killed: (\d+(,\d+)*)\+?
    """

    total_killed = 0
    total_displaced = 0
    total_kill_regexes = [
        '(\d+(?:,\d+)*)\+? killed in total',
        '(\d+(?:,\d+)*)\+? total killed',
        'total: (\d+(?:,\d+)*)\+? killed',
        'total killed: (\d+(?:,\d+)*)\+?',
    ]
    displaced_regexes = [
        '(\d+(?:,\d+)*)\+? displaced in total',
        '(\d+(?:,\d+)*)\+? total displaced',
        'total: (\d+(?:,\d+)*)\+? displaced',
        'total displaced: (\d+(?:,\d+)*)\+?',
    ]

    if 'casualties and losses' in header_tr_ranges:
        print('--- CASUALTIES ---')
        cas = header_tr_ranges['casualties and losses']
        for j in range(cas[0], cas[1]):
            cas_td = pq(trs.eq(j))('td')
            for td in cas_td:
                all_text = pq(td).text()
                # print(pq(td).text())
                for kill in total_kill_regexes:
                    g = re.findall(kill, all_text)
                    if len(g) > 0:
                        m = max(int(re.sub(r'[^\d]', '', x)) for x in g)
                        total_killed = max(total_killed, m)
                for displace in displaced_regexes:
                    g = re.findall(displace, all_text)
                    if len(g) > 0:
                        m = max(int(re.sub(r'[^\d]', '', x)) for x in g)
                        total_displaced = max(total_displaced, m)

    print('total killed:', total_killed)
    print('total displaced:', total_displaced)

    ret['total_killed'] = total_killed
    ret['total_displaced'] = total_displaced

    all_th = pq(b)('th')
    for th in (all_th.eq(i) for i in range(len(all_th))):
        # print(th)
        if th.text().lower() == 'date':
            print("FOUND DATE")
            date_text_i = 0
            date_con = th.siblings('td').contents()
            date = None
            for kk in range(len(date_con)):
                try:
                    date = date_con[kk].strip()
                    break
                except Exception as e:
                    print('error:', e)

            if date is not None:
                print(date)
                ret['raw_date'] = date
                if any(x in date for x in ['-', '–']):
                    dates = re.split(r'[-–]', date)
                    print(dates)
                    start_date_raw = dates[0].strip()
                    end_date_raw = dates[1].strip()
                    if end_date_raw.lower() == 'present' or end_date_raw == '':
                        end_date_raw = '19 March 2017'
                    if len(start_date_raw) <= 2:
                        # fix bad split
                        start_date_raw = ' '.join([start_date_raw] + end_date_raw.split()[1:])
                    
                    title_year = 2017
                    title_year_search = re.search('(\d+)', page_title)
                    if len(title_year_search) > 0:
                        title_year = int(re.sub('[^\d]', '', title_year_search[0]))

                    date_formats = [
                        "%d %B %Y",
                        "%B %Y",
                        "%Y",
                        "%d %B"
                    ]
                    start_date = None
                    end_date = None
                    for date_format in date_formats:
                        try:
                            start_date = datetime.datetime.strptime(start_date_raw, date_format).date()
                            if date_format == "%d %B":
                                start_date = start_date.replace(year=title_year)
                            break
                        except ValueError:
                            print(date_format, 'did not work for start')
                            continue
                    for date_format in date_formats:
                        try:
                            end_date = datetime.datetime.strptime(end_date_raw, date_format).date()
                            if date_format == "%d %B":
                                end_date = end_date.replace(year=title_year)
                            break
                        except ValueError:
                            print(date_format, 'did not work for end')
                            continue

                    if start_date is not None:
                        ret['start_date'] = start_date.strftime(db_date_format)
                    if end_date is not None:
                        ret['end_date'] = end_date.strftime(db_date_format)

                    print(start_date, end_date)

        elif th.text().lower() == 'location':
            print("FOUND LOCATION")
            locations = []
            location_anchors = pq(th.siblings('td').eq(0))('a')
            for an in (location_anchors.eq(i) for i in range(len(location_anchors))):
                locations.append({
                    'location': an.text(),
                    'href': an.attr('href'),
                    'title': an.attr('title')    
                })
            ret['locations'] = locations
   
    # info_headers = pq(b)('th[colspan="2"]')
    # for i in range(len(info_headers)):
    #     h = info_headers.eq(i)
    #     if h.text() in headers:
    #         print(h)
    #         print(h.parents())
    # print(info_headers)

    # find locations
    for i in range(len(ret['locations'])):
        loc = ret['locations'][i]['href']
        coords = location_url_to_coords(wiki_base_url + loc)

        ret['locations'][i]['coords'] = coords
        # print(coords)
        # loc = ret['locations'][i]['location']
        # resp = gmaps.places(query=loc)
        # print(resp)
        # if resp['status'] == 'OK' and len(resp['results']) > 0:
        #     first_geo = resp['results'][0]['geometry']['location']
        #     ret['locations'][i]['coords'] = {
        #         'lng': first_geo['lng'],
        #         'lat': first_geo['lat']
        #     }

    # print(json.dumps(ret))
    return ret

def location_url_to_coords(page_url):
    req = requests.get(page_url, headers={
        'authority': 'en.wikipedia.org',
        'method': 'GET',
        'path': '/wiki/War_in_Afghanistan_(2001%E2%80%932014)',
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'accept-encoding': 'gzip, deflate, sdch, br',
        'accept-language': 'en-US,en;q=0.8',
        'cache-control': 'max-age=0',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/56.0.2924.87 Safari/537.36'
    })
    d = pq(req.text)
    coords = d('span#coordinates')
    if coords:
        lat = coords('span.latitude').eq(0).text()
        lng = coords('span.longitude').eq(0).text()
    else:
        return None

    if lat == '' and lng == '':
        return None

    # print(lat, lng)
    lat_hemisphere = lat[-1]
    lng_hemisphere = lng[-1]

    lats = tuple(float(x) for x in (re.sub('[^\d\.]', ' ', lat[:-1]).split()))
    lngs = tuple(float(x) for x in (re.sub('[^\d\.]', ' ', lng[:-1]).split()))
    for i in range(3 - len(lats)):
        lats += (0.0,)
    for i in range(3 - len(lngs)):
        lngs += (0.0,)

    # convert to decimal
    lat_decimal = lats[0] + lats[1] / 60 + lats[2] / 3600
    lng_decimal = lngs[0] + lngs[1] / 60 + lngs[2] / 3600

    if lat_hemisphere.upper() == 'S':
        lat_decimal *= -1
    if lng_hemisphere.upper() == 'W':
        lng_decimal *= -1

    return {
        'lat': lat_decimal,
        'lng': lng_decimal
    }
    
events = json.load(open('conflicts-2016-2017.json', 'r'))
# events = json.load(open('test.json', 'r'))
big_ret = []
for info in events:
    for e_url in info['conflicts']:
        comb = wiki_base_url + e_url
        print('searching for:', comb)
        ret = conflict_page_to_info(comb)
        ret['conflict'] = e_url
        ret['wiki_year'] = info['year']
        big_ret.append(ret)
        time.sleep(0.25)

pickle.dump(big_ret, open('conflict-data-2016-2017.pkl', 'wb'))
json.dump(big_ret, open('conflict-data-2016-2017.json', 'w'))

# conflict_page_to_info('https://en.wikipedia.org/wiki/Operation_Atalanta')

# def year_json_

def conflict_json(start_year, end_year):
    j = []
    for year in range(start_year, end_year + 1):
        c = conflict_pages_from_year(year)
        j.append({
            'year': year,
            'conflicts': c
        })
        time.sleep(0.5)

    json.dump(j, open('conflicts-%s-%s.json' % (start_year, end_year), 'w'))
