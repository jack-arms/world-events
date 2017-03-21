'use strict';

var width = 800,
    height = 800,
    sens = 0.25,
    focused,
    conflicts_g,
    conflictTooltipDisappear,
    g_tip,
    g_over_tip,
    g_over_point;

// Setting projection
var projection = d3.geoOrthographic()
  .scale(350)
  .rotate([0, 0])
  .translate([width / 2, height / 2])
  .clipAngle(90);

var path = d3.geoPath()
  .projection(projection);

// SVG container
var svg = d3.select("body").append("svg")
  .attr("width", width)
  .attr("height", height);

// Adding water
svg.append("path")
  .datum({type: "Sphere"})
  .attr("class", "water")
  .attr("d", path);

g_tip = d3.select('body')
    .append('div')
    .attr('class', 'conflictTooltip')
    .style('border', '1px solid steelblue')
    .style('padding', '5px')
    .style('position', 'absolute')
    .style('overflow', 'hidden')
    .style('display', 'none')
    .on('mouseover', function(d, i) {
        g_over_tip = true;
    })
    .on('mouseout', function(d, i) {
        g_over_tip = false;
        if (!g_over_tip && !g_over_point) {
            g_tip.style('display', 'none');  // on mouseout hide tip
        }
    });

var countryList = d3.select('select[name="countries"]');

queue()
  .defer(d3.json, "world-110m.json")
  .defer(d3.tsv, "world-110m-country-names.tsv")
  .await(ready);

// Main function
function ready(error, world, countryData) {
  var countryById = {},
      countries = topojson.feature(world, world.objects.countries)
        .features;

  countryData.forEach(function(d) {
    countryById[d.id] = d.name;
    let option = countryList.append("option");
    option.text(d.name);
    option.property("value", d.id);
  });

  var dragEvent = d3.drag()
    .subject(function() {
        var r = projection.rotate(); 
        return {x: r[0] / sens, y: -r[1] / sens}; 
    })
    .on("drag", function() {
      var rotate = projection.rotate();
      projection.rotate([d3.event.x * sens, -d3.event.y * sens, rotate[2]]);
      svg.selectAll("path.land").attr("d", path);
      // svg.selectAll("path.conflict_loc").attr("d", path);
      svg.selectAll(".focused").classed("focused", focused = false);
      updateConflicts(conflicts_g);
    });

  // Drawing countries on the globe
  var world = svg.selectAll("path.land")
    .data(countries)
    .enter().append("path")
    .attr("class", "land")
    .attr("d", path)

  // Drag event
  .call(dragEvent);

  svg.selectAll("path.water")
    .call(dragEvent);

  // Country focus on option select
  d3.select("select").on("change", function() {
    var rotate = projection.rotate(),
      focusedCountry = country(countries, this),
      p = d3.geoCentroid(focusedCountry);
    svg.selectAll(".focused").classed("focused", focused = false);

    // Globe rotating
    (function transition() {
      d3.transition()
      .duration(2500)
      .tween("rotate", function() {
        var r = d3.interpolate(projection.rotate(), [-p[0], -p[1]]);
        return function(t) {
          projection.rotate(r(t));
          svg.selectAll("path.land,path.water").attr("d", path)
          .classed("focused", function(d, i) {
            return d.id == focusedCountry.id ? focused = d : false;
          });
          updateConflicts(conflicts_g);
        };
      });
    })();
  });

  function country(cnt, sel) { 
    for(var i = 0, l = cnt.length; i < l; i++) {
      if(cnt[i].id == sel.value) {return cnt[i];}
    }
  };

  function updateConflicts(conflicts) {
    console.log("updating...");
    svg.selectAll(".conflict_loc")
      .data(conflicts)
      .attr('d', function(d) {
          return path(
            d3.geoCircle()
              .center([d.locations[0].lng, d.locations[0].lat])
              .radius(1)()
          );
      });
  }

  d3.select("#getdata").on("click", function() {
    $.ajax({
      url: "conflicts.php",
      success: function(result) {
        loadConflictData(result['results']);
      }
    })
  });

  function loadConflictData(conflicts) {
    conflicts_g = conflicts;
    let path = d3.geoPath(projection);
    let circle = svg.selectAll(".conflict_loc")
       .data(conflicts)
       .enter().append("path")
       .attr('class', 'conflict_loc')
       .attr('d', function(d) {
          return path(d3.geoCircle()
            .center([d.locations[0].lng, d.locations[0].lat])
            .radius(1)());
       });
    circle.on("mouseover", function(d) {
      g_over_point = true;

      if (d.partof.length > 0) {
        var partof_html = '';
        d.partof.forEach(function(d) {
          partof_html += '<li><a href="www.en.wikipedia.org/wiki/"' + d.title + '>' + "www.en.wikipedia.org/wiki" + d.title + '</a></li>'
        })
        partof_html = '<ul>' + partof_html + '</ul>';
      }
      var bell_html = '';
      if (d.belligerents.length > 0) {
        d.belligerents.forEach(function(d) {
           let name = d.text;
           if (name == null) {
              name = d.title;
           }
           if (name != null && name.length > 0) {
              bell_html += '<li><a href="www.en.wikipedia.org/wiki' + d.href + '">' + name + '</a></li>'
           }
        })
      }
      var all_html = '<p><strong class="strong-conflict">Conflict:</strong> <a href="www.en.wikipedia.org/wiki"' + d.title + '>' + "www.en.wikipedia.org/wiki" + d.title + '</a></p>';
      if (d.partof.length > 0) {
        all_html += '<strong>Part of:</strong>' + partof_html;
      }
      if (d.belligerents.length > 0) {
        all_html += '<strong>Belligerents:</strong>' + bell_html;
      }
      all_html += '<p><strong>People killed:</strong> ' + d.total_killed + '</p>'
      all_html += '<p><strong>People displaced:</strong> ' + d.total_displaced + '</p>'
      console.log(all_html);
      g_tip.transition().duration(0); // cancel any pending transition
      g_tip.style('top', d3.event.pageY - 20 + 'px');
      g_tip.style('left', (d3.event.pageX - 2) + 'px');
      g_tip.style('display', 'block')
      g_tip.html(all_html)
      g_over_tip = true;
    })
    .on('mouseout', function(d) {
      g_over_point = false;
      if (!g_over_point  && !g_over_tip ) {
          console.log("mouse is not over tool tip!");
          g_tip.style('display', 'none'); // give user 500ms to move to tooltip
        }
    });
  }
};