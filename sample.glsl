// improved version of https://www.shadertoy.com/view/MlVSWc
// === SVG Player ====      short spec: https://www.w3.org/TR/2008/REC-SVGTiny12-20081222/paths.html

#define N 20.  // splines discretization. Lower it on slow GPUs
// absolute main SVG commands
#define M(x,y)             x0 = xx0 = x;   y0 = yy0 = y;
#define L(x,y)             d = min(d, line(uv, vec2(xx0,yy0), vec2(x,y)) ); xx0=x,yy0=y;
#define C(x1,y1,x2,y2,x,y) d = min(d, bezier(uv, vec2(xx0,yy0), vec2(x1,y1),vec2(x2,y2), vec2(x,y)) ); xx0=x,yy0=y; 
#define H(x)               d = min(d, line(uv, vec2(xx0,yy0), vec2(x,yy0)) ); xx0=x;
#define V(y)               d = min(d, line(uv, vec2(xx0,yy0), vec2(xx0,y)) ); yy0=y;
#define Z                  d = min(d, line(uv, vec2(xx0,yy0), vec2(x0,y0)) );
// relative main SVG commands
#define m(x,y)             M(xx0+x,yy0+y)
#define l(x,y)             L(xx0+x,yy0+y)
#define c(x1,y1,x2,y2,x,y) C(xx0+x1,yy0+y1,xx0+x2,yy0+y2,xx0+x,yy0+y)
#define h(x)               H(xx0+x)
#define v(y)               V(yy0+y)
#define z                  Z

#define style(f,c)         fill=f; S=1.; COL = mod(vec4((c)/65536,(c)/256,c,1),256.)/255.;
#define path(cmd)          d = 1e38; cmd; draw(d,O);

float bezier(vec2,vec2,vec2,vec2,vec2);
float line(vec2,vec2,vec2);
void  draw(float,inout vec4);
const float FILL=1., CONTOUR=0.;
vec4 COL = vec4(0); float fill=FILL, S=1., contrast=1.;  // style state
float d = 1e38;   // global to allow unique distance field

// === SVG drawing ===============================================================
void SVG(vec2 uv, inout vec4 O) 
{
    float xx0, yy0, x0, y0; // d = 1e38; 
    uv.y -= .3;
    uv.x -= .5;
    uv *= 550.;                             // scaling
    contrast = 1.;

// Copy-paste your SVG pathes here.  Slight adaptations : 
//  - add () around command params and  comma between points, 
//  - split polylines and polybéziers into sets of 1 vs 3 pairs of coordinates
//  - path( style( FILL/CONTOUR, color(hexa) )
//          commands 
//        )    


    // PASTE PYTHON SCRIPT RESULT HERE

}

// --- spline interpolation ( inspired from revers https://www.shadertoy.com/view/MlGSz3 )
vec2 interpolate(vec2 G1, vec2 G2, vec2 G3, vec2 G4, float t)
{
    vec2 A = G4-G1 + 3.*(G2-G3),
         B = 3.*(G1-2.*G2+G3),
         C = 3.*(G2-G1),
         D = G1;
    return t * (t * (t * A + B) + C) + D;
}


float line(vec2 p, vec2 a, vec2 b) 
{
	vec2 pa = p - a, ba = b - a,
	     d = pa - ba * clamp(dot(pa, ba) / dot(ba, ba) , 0., 1.); // distance to segment
    if  ( (a.y>p.y) != (b.y>p.y) &&
           pa.x < ba.x * pa.y / ba.y ) S = -S;     // track interior vs exterior
	return dot(d,d); //length(d);                  // optimization by deferring sqrt
}
// interior detection (sign S): ( thanks TimoKinnunen https://www.shadertoy.com/view/4lySWd )
// see http://web.archive.org/web/20161116163747/https://www.ecse.rpi.edu/Homepages/wrf/Research/Short_Notes/pnpoly.html - previously on https://www.ecse.rpi.edu/Homepages/wrf/Research/Short_Notes/pnpoly.html

float bezier( vec2 uv, vec2 A, vec2 B, vec2 C, vec2 D)    
{
    //float d = 1e5;                               // for global field
    vec2 p = A;
    for (float t = 1.; t <= N; t++) {
        vec2 q = interpolate(A, B, C, D, t/N);
        float l = line(uv, p, q);
        d = min(d, l );
		p = q;
	}
	return d;
}

void draw(float d, inout vec4 O) 
{
    d = min(sqrt(d)*contrast*2.,1.);             // optimization by deferring sqrt here
    O = mix(COL, O, fill>0. ? .5+.5*S*d : d);    // paint 
}

void mainImage(out vec4 O, vec2 U) 
{
    O = vec4(1);
    vec2 R = iResolution.xy;
    U.y = R.y-U.y; U /= R.x;
	SVG( U, O );
}

