'use strict';

var width = 1400,
    height = 800,
    sens = 0.25,
    focused,
    conflicts_g,
    conflictTooltipDisappear,
    g_tip,
    g_over_tip,
    g_over_point,
    g_curr_proj = "ortho",
    g_can_drag = true;

var projs = {
  'ortho': d3.geoOrthographic()
              .scale(350)
              .rotate([0, 0])
              .translate([width / 2, height / 2])
              .clipAngle(90),
  'flat': d3.geoEquirectangular()
              .scale(200)
              .rotate([0, 0])
              .translate([width / 2, height / 2])
}

// Setting projection
var projection = projs['ortho'];

var path = d3.geoPath()
  .projection(projection);

// SVG container
var svg = d3.select("body").append("svg")
  .attr("width", width)
  .attr("height", height);

// Adding water
function addWater() {
  svg.insert("path", ":first-child")
      .datum({type: "Sphere"})
      .attr("class", "water")
      .attr("d", path)
      // .call(dragEvent);
}

function removeWater() {
  console.log('remove water!');
  svg.selectAll("path.water").remove();
}

var dragEvent = d3.drag()
  .subject(function() {
      var r = projection.rotate(); 
      return {x: r[0] / sens, y: -r[1] / sens}; 
  })
  .on("drag", function() {
    if (g_can_drag) {
      var rotate = projection.rotate();
      projection.rotate([d3.event.x * sens, -d3.event.y * sens, rotate[2]]);
      path.projection(projection);
      svg.selectAll("path.land,path.water").attr("d", path);
      svg.selectAll("path.conflict_loc").attr("d", createConflictLoc(path));
      svg.selectAll(".focused").classed("focused", focused = false);
      // updateConflicts(conflicts_g);
    }
  });

// addWater();

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
svg.call(dragEvent);

var projectionRadios = d3.selectAll('input[name="projection"]');
projectionRadios.on('change', function() {
  console.log(this);
  var newValue = this.value;
  if (newValue !== g_curr_proj) {
    g_curr_proj = newValue;
    if (newValue !== 'ortho') {
      var trans = resetRotation();
      var n = 0;
      trans.on('start', () => n++);
      trans.on('end', () => {
        n--;
        if (!n) {
          console.log("ending transition, moving to next one");
          projUpdate(newValue, projs[newValue])
        }
      });
    } else {
      projUpdate(newValue, projs[newValue])
    }
  }
});

function projUpdate(newProjName, newProj) {
  if (newProjName !== 'ortho') {
    // removeWater();
  }
  if (newProjName === 'ortho') {
    // newProj.clipAngle(90);
  }
  var n = 0;
  var trans = svg.selectAll("path").transition()
      .duration(2000)
      .attrTween("d", function(d) {
         if (d3.select(this).classed('conflict_loc')) {
            return createConflictLoc(projectionTween(projection, newProj))(d);
         } else {
            return projectionTween(projection, newProj)(d);
         }
      })
      .on('start', () => n++)
      .on('end', () => {
          n--;
          if (!n) {
            projection = newProj;
            if (newProjName === 'ortho') {
              svg.call(dragEvent);
              // projection.clipAngle(90);
              path.projection(projection);
              svg.selectAll("path.land,path.water").attr("d", path);
              svg.selectAll("path.conflict_loc").attr("d", createConflictLoc(path));
              g_can_drag = true;
            } else {
              g_can_drag = false;
            }
          }
      });
}

function projectionTween(projection0, projection1) {
  return function(d) {
    var t = 0;

    var projection = d3.geoProjection(project)
        .scale(1)
        .translate([width / 2, height / 2]);

    var path = d3.geoPath()
        .projection(projection);

    function project(lam, phi) {
      lam *= 180 / Math.PI, phi *= 180 / Math.PI;
      var p0 = projection0([lam, phi]), p1 = projection1([lam, phi]);
      return [(1 - t) * p0[0] + t * p1[0], (1 - t) * -p0[1] + t * -p1[1]];
    }

    return function(_) {
      t = _;
      if (g_curr_proj === 'ortho') {
        projection.clipAngle(180 - t * 90);
      }
      // path.projection(projection);
      return path(d);
    };
  };
}

d3.select('#resetrot').on('click', resetRotation);

function resetRotation() {
  return transitionRotateTo([0, 0, 0]);
}

function transitionRotateTo(rotation) {
  var trans = svg.selectAll('path').transition()
    .duration(2500)
    .ease(d3.easeCubic)
    .tween("rotate", function() {
      var r = d3.interpolate(projection.rotate(), rotation);
      var that = this;
      // console.log(that);
      // console.log(createConflictLoc);
      return function(t) {
        projection.rotate(r(t));
        let el = d3.select(that);
        if (el.classed('conflict_loc')) {
          el.attr("d", createConflictLoc(path));
        } else {
          el.attr("d", path);
        }
      };
    });
  // if (start) {
  //   trans.on('start', start);
  // }
  // if (end) {
  //   trans.on('end', end);
  // }
  return trans;
} 

function removeFocus() {
  svg.selectAll('.focus')
}

function createConflictLoc(path) {
  return function(d) {
    return path(
      d3.geoCircle()
        .center([d.locations[0].lng, d.locations[0].lat])
        .radius(1)()
    );
  }
}

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

  // Drawing countries on the globe
  var world = svg.selectAll("path.land")
    .data(countries)
    .enter().append("path")
    .attr("class", "land")
    .attr("d", path)
    // .call(dragEvent);

  // Country focus on option select
  d3.select("select").on("change", function() {
    var rotate = projection.rotate(),
      focusedCountry = country(countries, this),
      p = d3.geoCentroid(focusedCountry);
    svg.selectAll(".focused").classed("focused", focused = false);

    // Globe rotating
    var trans = transitionRotateTo([-p[0], -p[1]]);
    trans.on('start', function(d) {
      let el = d3.select(this);
      console.log("this:");
      console.log(this);
      console.log("d:");
      console.log(d);
      console.log("el:");
      console.log(el);
      console.log("country:");
      console.log(focusedCountry);
      if (el.classed('land')) {
        el.classed("focused", function(d, i) {
           return d.id == focusedCountry.id ? focused = d : false;
        });
      }
    });
  });

  function country(cnt, sel) { 
    for(var i = 0, l = cnt.length; i < l; i++) {
      if(cnt[i].id == sel.value) {return cnt[i];}
    }
    console.log("no country found?????");
    return null;
  };

  // function updateConflicts(conflicts) {
  //   // console.log("updating...");
  //   svg.selectAll(".conflict_loc")
  //     .data(conflicts)
  //     .attr('d', function(d) {
  //         return path(
  //           d3.geoCircle()
  //             .center([d.locations[0].lng, d.locations[0].lat])
  //             .radius(1)()
  //         );
  //     });
  // }

  d3.select("#getdata").on("click", function() {
    $.ajax({
      url: "/conflicts",
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