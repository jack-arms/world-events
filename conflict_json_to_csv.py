import csv
import json

belligerent = open('belligerent.csv', 'w')           
conflict = open('conflict.csv', 'w')   
conflictpartof = open('conflictpartof.csv', 'w')          
involvedin =open('involvedin.csv', 'w')                 
locatedin = open('locatedin.csv', 'w')                  
location = open('location.csv', 'w')

belligerent_writer = csv.DictWriter(belligerent, fieldnames=['href', 'text', 'title'], escapechar='\\', delimiter=',', quoting=csv.QUOTE_MINIMAL)
conflict_writer = csv.DictWriter(conflict, fieldnames=['href', 'raw_date', 'start_date', 'end_date', 'wiki_year', 'total_killed', 'total_displaced'], escapechar='\\', delimiter=',', quoting=csv.QUOTE_MINIMAL)
conflictpartof_writer = csv.DictWriter(conflictpartof, fieldnames=['conflict_href', 'main_conflict_href'], escapechar='\\', delimiter=',', quoting=csv.QUOTE_MINIMAL)
involvedin_writer = csv.DictWriter(involvedin, fieldnames=['belligerent_href', 'conflict_href'], delimiter=',', escapechar='\\', quoting=csv.QUOTE_MINIMAL)
locatedin_writer = csv.DictWriter(locatedin, fieldnames=['conflict_href', 'location_href'], delimiter=',', escapechar='\\', quoting=csv.QUOTE_MINIMAL)
location_writer = csv.DictWriter(location, fieldnames=['href', 'location', 'title', 'lat', 'lng'], delimiter=',', escapechar='\\', quoting=csv.QUOTE_MINIMAL)

data = json.load(open('conflict-data-2016-2017.json', 'r'))

added_belligerents = set()
added_conflicts = set()
added_locations = set()

added_conflictpartof = set()
added_locatedin = set()
added_involvedin = set()
added_part_conflicts = set()

belligerent_writer.writeheader()
conflict_writer.writeheader()
conflictpartof_writer.writeheader()
involvedin_writer.writeheader()
locatedin_writer.writeheader()
location_writer.writeheader()

for datum in data:
	if 'raw_date' in datum:
		raw_date = datum['raw_date']
	else:
		raw_date = ''

	if 'start_date' in datum:
		start_date = datum['start_date']
	else:
		start_date = '\\N'

	if 'end_date' in datum:
		end_date = datum['end_date']
	else:
		end_date = '\\N'


	if datum['conflict'] not in added_conflicts:
		# 'href', 'raw_date', 'start_date', 'end_date', 'wiki_year', 'total_killed', 'total_displaced'
		conflict_writer.writerow({
			'href': datum['conflict'],
			'raw_date': raw_date,
			'start_date': start_date,
			'end_date': end_date,
			'wiki_year': datum['wiki_year'],
			'total_killed': datum['total_killed'],
			'total_displaced': datum['total_displaced']
		})
		added_conflicts.add(datum['conflict'])

	for b_list in datum['belligerents']:
		for b in b_list:
			if (b['href'], datum['conflict']) not in added_involvedin:
				added_involvedin.add((b['href'], datum['conflict']))
				involvedin_writer.writerow({
					'belligerent_href': b['href'],
					'conflict_href': datum['conflict']
				})

			if b['href'] not in added_belligerents:
				added_belligerents.add(b['href'])
				belligerent_writer.writerow({
					'href': b['href'],
					'text': b['text'],
					'title': b['title']	
				})

	for loc in datum['locations']:
		if loc['href'] not in added_locations:
			added_locations.add(loc['href'])
			lng = '\\N'
			lat = '\\N'
			if loc['coords'] is not None:
				lng = '%.4f' % float(loc['coords']['lng'])
				lat = '%.4f' % float(loc['coords']['lat'])

			# 'href', 'location', 'title', 'lat', 'lng'
			location_writer.writerow({
				'href': loc['href'],
				'location': loc['location'],
				'title': loc['title'],
				'lat': lat,
				'lng': lng
			})

		if (datum['conflict'], loc['href']) not in added_locatedin:
			added_locatedin.add((datum['conflict'], loc['href']))
			locatedin_writer.writerow({
				'conflict_href': datum['conflict'],
				'location_href': loc['href']	
			})

	for part in datum['partof']:
		if part['href'] not in added_part_conflicts:
			added_part_conflicts.add(part['href'])
		if (datum['conflict'], part['href']) not in added_conflictpartof:
			added_conflictpartof.add((datum['conflict'], part['href']))
			conflictpartof_writer.writerow({
				'conflict_href': datum['conflict'],
				'main_conflict_href': part['href']	
			})
