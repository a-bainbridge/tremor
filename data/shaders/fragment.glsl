#version 330

out vec4 outputColor;

in vec3 fnormal;
varying vec3 fcolor;
varying vec3 fposition;
varying vec2 texCoord;

uniform sampler2D texColor;
uniform bool isTextured;

const vec3 ambient = vec3(0.2);

const vec3 look = vec3(0., 0., 1.);
const vec3 light = vec3(-5., -5., 5.);
const vec3 light_col = vec3(1.);
const float light_strength = 1.0;

vec2 getTexPos (vec3 p, vec3 n) {
    //does good approximations for textures on coordinate planes
    return ((p.xz*n.y) + (p.xy*n.z) + (p.yz*n.x));
}
void main()
{
    vec3 col = fcolor * ambient;
    if (isTextured)
        col = texture2D(texColor, texCoord).rgb * ambient;
    vec3 normal = normalize(fnormal);
    vec3 light_dir = normalize(light - fposition);
    float diffuse = max(dot(light_dir, normal), 0.);
    float specular = pow(max(dot(look, -reflect(normal, light_dir)), 0.), 16.);
//    float specular = 0.00001 * length(fnormal);
    col += (diffuse * 0.5 + specular * 0.5) * light_col * light_strength;
//    col *= fcolor;
//    col *= fposition * 5.;
//    col *= mod(fposition, 0.3) * 3.33;
    outputColor = vec4(col, 1.);
}