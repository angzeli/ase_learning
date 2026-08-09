#version 3.6;
#include "colors.inc"
#include "finish.inc"

global_settings {assumed_gamma 2.2 max_trace_level 6}
background {color White transmit 1.0}
camera {orthographic
  right -17.38*x up 6.93*y
  direction 1.00*z
  location <0,0,50.00> look_at <0,0,0>}


light_source {<  2.00,   3.00,  40.00> color White
  area_light <0.70, 0, 0>, <0, 0.70, 0>, 3, 3
  adaptive 1 jitter}
// no fog
#declare simple = finish {phong 0.7 ambient 0.4 diffuse 0.55}
#declare pale = finish {ambient 0.9 diffuse 0.30 roughness 0.001 specular 0.2 }
#declare intermediate = finish {ambient 0.4 diffuse 0.6 specular 0.1 roughness 0.04}
#declare vmd = finish {ambient 0.2 diffuse 0.80 phong 0.25 phong_size 10.0 specular 0.2 roughness 0.1}
#declare jmol = finish {ambient 0.4 diffuse 0.6 specular 1 roughness 0.001 metallic}
#declare ase2 = finish {ambient 0.2 brilliance 3 diffuse 0.6 metallic specular 0.7 roughness 0.04 reflection 0.15}
#declare ase3 = finish {ambient 0.4 brilliance 2 diffuse 0.6 metallic specular 1.0 roughness 0.001 reflection 0.0}
#declare glass = finish {ambient 0.4 diffuse 0.35 specular 1.0 roughness 0.001}
#declare glass2 = finish {ambient 0.3 diffuse 0.3 specular 1.0 reflection 0.25 roughness 0.001}
#declare Rcell = 0.050;
#declare Rbond = 0.100;

#macro atom(LOC, R, COL, TRANS, FIN)
  sphere{LOC, R texture{pigment{color COL transmit TRANS} finish{FIN}}}
#end
#macro constrain(LOC, R, COL, TRANS FIN)
union{torus{R, Rcell rotate 45*z texture{pigment{color COL transmit TRANS} finish{FIN}}}
     torus{R, Rcell rotate -45*z texture{pigment{color COL transmit TRANS} finish{FIN}}}
     translate LOC}
#end

cylinder {< -6.96,  -2.24,  -0.36>, <  3.20,  -2.24,  -0.36>, Rcell pigment {Black}}
cylinder {< -1.88,  -0.71,  -9.02>, <  8.28,  -0.71,  -9.02>, Rcell pigment {Black}}
cylinder {< -1.88,  -0.71,  -9.02>, <  8.28,  -0.71,  -9.02>, Rcell pigment {Black}}
cylinder {< -6.96,  -2.24,  -0.36>, <  3.20,  -2.24,  -0.36>, Rcell pigment {Black}}
cylinder {< -6.96,  -2.24,  -0.36>, < -1.88,  -0.71,  -9.02>, Rcell pigment {Black}}
cylinder {<  3.20,  -2.24,  -0.36>, <  8.28,  -0.71,  -9.02>, Rcell pigment {Black}}
cylinder {<  3.20,  -2.24,  -0.36>, <  8.28,  -0.71,  -9.02>, Rcell pigment {Black}}
cylinder {< -6.96,  -2.24,  -0.36>, < -1.88,  -0.71,  -9.02>, Rcell pigment {Black}}
atom(< -6.96,  -1.98,  -1.80>, 1.32, rgb <0.78, 0.50, 0.20>, 0.0, ase3) // #0
atom(< -6.96,  -0.19,   0.00>, 1.32, rgb <0.78, 0.50, 0.20>, 0.0, ase3) // #1
atom(< -5.69,   1.50,  -0.45>, 0.66, rgb <1.00, 0.05, 0.05>, 0.0, ase3) // #2
atom(< -5.69,  -1.60,  -3.97>, 1.32, rgb <0.78, 0.50, 0.20>, 0.0, ase3) // #3
atom(< -5.69,   0.19,  -2.16>, 1.32, rgb <0.78, 0.50, 0.20>, 0.0, ase3) // #4
atom(< -4.42,   1.88,  -2.61>, 0.66, rgb <1.00, 0.05, 0.05>, 0.0, ase3) // #5
atom(< -4.42,  -1.22,  -6.13>, 1.32, rgb <0.78, 0.50, 0.20>, 0.0, ase3) // #6
atom(< -4.42,   0.57,  -4.33>, 1.32, rgb <0.78, 0.50, 0.20>, 0.0, ase3) // #7
atom(< -3.15,   2.26,  -4.78>, 0.66, rgb <1.00, 0.05, 0.05>, 0.0, ase3) // #8
atom(< -3.15,  -0.84,  -8.30>, 1.32, rgb <0.78, 0.50, 0.20>, 0.0, ase3) // #9
atom(< -3.15,   0.95,  -6.49>, 1.32, rgb <0.78, 0.50, 0.20>, 0.0, ase3) // #10
atom(< -1.88,   2.64,  -6.94>, 0.66, rgb <1.00, 0.05, 0.05>, 0.0, ase3) // #11
atom(< -4.42,  -1.98,  -1.80>, 1.32, rgb <0.78, 0.50, 0.20>, 0.0, ase3) // #12
atom(< -4.42,  -0.19,   0.00>, 1.32, rgb <0.78, 0.50, 0.20>, 0.0, ase3) // #13
atom(< -3.15,   1.50,  -0.45>, 0.66, rgb <1.00, 0.05, 0.05>, 0.0, ase3) // #14
atom(< -3.15,  -1.60,  -3.97>, 1.32, rgb <0.78, 0.50, 0.20>, 0.0, ase3) // #15
atom(< -3.15,   0.19,  -2.16>, 1.32, rgb <0.78, 0.50, 0.20>, 0.0, ase3) // #16
atom(< -1.88,   1.88,  -2.61>, 0.66, rgb <1.00, 0.05, 0.05>, 0.0, ase3) // #17
atom(< -1.88,  -1.22,  -6.13>, 1.32, rgb <0.78, 0.50, 0.20>, 0.0, ase3) // #18
atom(< -1.88,   0.57,  -4.33>, 1.32, rgb <0.78, 0.50, 0.20>, 0.0, ase3) // #19
atom(< -0.61,   2.26,  -4.78>, 0.66, rgb <1.00, 0.05, 0.05>, 0.0, ase3) // #20
atom(< -0.61,  -0.84,  -8.30>, 1.32, rgb <0.78, 0.50, 0.20>, 0.0, ase3) // #21
atom(< -0.61,   0.95,  -6.49>, 1.32, rgb <0.78, 0.50, 0.20>, 0.0, ase3) // #22
atom(<  0.66,   2.64,  -6.94>, 0.66, rgb <1.00, 0.05, 0.05>, 0.0, ase3) // #23
atom(< -1.88,  -1.98,  -1.80>, 1.32, rgb <0.78, 0.50, 0.20>, 0.0, ase3) // #24
atom(< -1.88,  -0.19,   0.00>, 1.32, rgb <0.78, 0.50, 0.20>, 0.0, ase3) // #25
atom(< -0.61,   1.50,  -0.45>, 0.66, rgb <1.00, 0.05, 0.05>, 0.0, ase3) // #26
atom(< -0.61,  -1.60,  -3.97>, 1.32, rgb <0.78, 0.50, 0.20>, 0.0, ase3) // #27
atom(< -0.61,   0.19,  -2.16>, 1.32, rgb <0.78, 0.50, 0.20>, 0.0, ase3) // #28
atom(<  0.66,   1.88,  -2.61>, 0.66, rgb <1.00, 0.05, 0.05>, 0.0, ase3) // #29
atom(<  0.66,  -1.22,  -6.13>, 1.32, rgb <0.78, 0.50, 0.20>, 0.0, ase3) // #30
atom(<  0.66,   0.57,  -4.33>, 1.32, rgb <0.78, 0.50, 0.20>, 0.0, ase3) // #31
atom(<  1.93,   2.26,  -4.78>, 0.66, rgb <1.00, 0.05, 0.05>, 0.0, ase3) // #32
atom(<  1.93,  -0.84,  -8.30>, 1.32, rgb <0.78, 0.50, 0.20>, 0.0, ase3) // #33
atom(<  1.93,   0.95,  -6.49>, 1.32, rgb <0.78, 0.50, 0.20>, 0.0, ase3) // #34
atom(<  3.20,   2.64,  -6.94>, 0.66, rgb <1.00, 0.05, 0.05>, 0.0, ase3) // #35
atom(<  0.66,  -1.98,  -1.80>, 1.32, rgb <0.78, 0.50, 0.20>, 0.0, ase3) // #36
atom(<  0.66,  -0.19,   0.00>, 1.32, rgb <0.78, 0.50, 0.20>, 0.0, ase3) // #37
atom(<  1.93,   1.50,  -0.45>, 0.66, rgb <1.00, 0.05, 0.05>, 0.0, ase3) // #38
atom(<  1.93,  -1.60,  -3.97>, 1.32, rgb <0.78, 0.50, 0.20>, 0.0, ase3) // #39
atom(<  1.93,   0.19,  -2.16>, 1.32, rgb <0.78, 0.50, 0.20>, 0.0, ase3) // #40
atom(<  3.20,   1.88,  -2.61>, 0.66, rgb <1.00, 0.05, 0.05>, 0.0, ase3) // #41
atom(<  3.20,  -1.22,  -6.13>, 1.32, rgb <0.78, 0.50, 0.20>, 0.0, ase3) // #42
atom(<  3.20,   0.57,  -4.33>, 1.32, rgb <0.78, 0.50, 0.20>, 0.0, ase3) // #43
atom(<  4.47,   2.26,  -4.78>, 0.66, rgb <1.00, 0.05, 0.05>, 0.0, ase3) // #44
atom(<  4.47,  -0.84,  -8.30>, 1.32, rgb <0.78, 0.50, 0.20>, 0.0, ase3) // #45
atom(<  4.47,   0.95,  -6.49>, 1.32, rgb <0.78, 0.50, 0.20>, 0.0, ase3) // #46
atom(<  5.74,   2.64,  -6.94>, 0.66, rgb <1.00, 0.05, 0.05>, 0.0, ase3) // #47

// no constraints
