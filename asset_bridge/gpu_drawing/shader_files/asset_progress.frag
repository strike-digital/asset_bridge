uniform vec4 color;
uniform sampler2D image;

in vec2 Uv;
out vec4 fragColor;

bool compare(in vec2 a, in vec2 b, in float threshold) {
  vec2 diff = abs(a - b);
  return diff.x < threshold && diff.y < threshold;
}

// p = position
// b.x = width
// b.y = height
// r.x = roundness top-right  
// r.y = roundness boottom-right
// r.z = roundness top-left
// r.w = roundness bottom-left
float sdRoundedBox(in vec2 p, in vec2 b, in vec4 r) {
  r.xy = (p.x > 0.0) ? r.xy : r.zw;
  r.x = (p.y > 0.0) ? r.x : r.y;
  vec2 q = abs(p) - b + r.x;
  return min(max(q.x, q.y), 0.0) + length(max(q, 0.0)) - r.x;
}

// signed distance to a 2D triangle
float sdTriangle(in vec2 p, in vec2 p0, in vec2 p1, in vec2 p2) {
  vec2 e0 = p1 - p0;
  vec2 e1 = p2 - p1;
  vec2 e2 = p0 - p2;

  vec2 v0 = p - p0;
  vec2 v1 = p - p1;
  vec2 v2 = p - p2;

  vec2 pq0 = v0 - e0 * clamp(dot(v0, e0) / dot(e0, e0), 0.0, 1.0);
  vec2 pq1 = v1 - e1 * clamp(dot(v1, e1) / dot(e1, e1), 0.0, 1.0);
  vec2 pq2 = v2 - e2 * clamp(dot(v2, e2) / dot(e2, e2), 0.0, 1.0);

  float s = e0.x * e2.y - e0.y * e2.x;
  vec2 d = min(min(vec2(dot(pq0, pq0), s * (v0.x * e0.y - v0.y * e0.x)), vec2(dot(pq1, pq1), s * (v1.x * e1.y - v1.y * e1.x))), vec2(dot(pq2, pq2), s * (v2.x * e2.y - v2.y * e2.x)));

  return -sqrt(d.x) * sign(d.y);
}

void main()
{
  vec2 uv = (Uv - .5) * 2.;
  float roundness = .2;
  float size = .99;
  float invSize = 1. - size;
  vec2 boxUv = uv;
  float triSize = .2;
  boxUv = boxUv * (1. + triSize) - triSize;
  boxUv.x += triSize * 2;
  float dist = sdRoundedBox(boxUv, vec2(size), vec4(roundness, roundness, roundness, 0));

  vec2 p1 = vec2(-1.0 + invSize, -1.0 + invSize);
  vec2 p2 = vec2(-0.7 + invSize, -1.0 + invSize);
  vec2 p3 = vec2(-1.0 + invSize, -1.4 + invSize);
  float bodyDist = min(sdTriangle(boxUv, p1, p2, p3), dist);

  vec2 insideUv = boxUv * 1.1;
  float insideDist = sdRoundedBox(insideUv, vec2(size), vec4(roundness));
  dist = bodyDist * insideDist;
  dist = dist / fwidth(dist);
  // if(dist > 1.1) {
  //   discard;
  // };
  // dist = sdTriangle(boxuv, p1, p2, p3);

  // dist = float(dist < 0.0);
  // boxuv = fract(boxuv);
  // fragColor = blender_srgb_to_framebuffer_space(vec4(boxuv, 0, 1));
  // fragColor = blender_srgb_to_framebuffer_space(vec4(dist, dist, dist, 1));
  // vec4 outColor = color * (1 - dist); 
  vec4 borderColor = clamp(color * vec4(1- dist), vec4(0.), vec4(1.)); 
  // outColor.w = 1. - dist;
  
  vec2 imageUv = insideUv / 2 + .5;
  vec4 image = texture2D(image, imageUv);

  // Stop image repeating
  image = image * float(compare(imageUv, vec2(.5), .5));
  // image.w = outColor.w;
  // outColor = vec4(image.w) * outColor * .00001;

  vec4 outColor = mix(image, borderColor, borderColor.w);
  // vec4 outColor = vec4(borderColor.w, borderColor.w, borderColor.w, 1);
  // outColor.w = borderColor.w;
  // vec4 outColor = image + borderColor;
  fragColor = blender_srgb_to_framebuffer_space(outColor);
  // fragColor = vec4(1);
  // fragColor = blender_srgb_to_framebuffer_space(vec4(Uv, 0, 1));
}