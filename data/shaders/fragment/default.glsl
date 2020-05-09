#version 330

out vec4 outputColor;

in vec4 cameraPosition;
in vec3 fnormal;
in vec3 fcolor;
in vec3 fposition;
in vec2 texCoord;

uniform sampler2D texColor;
uniform bool useTexColor;
uniform float time;

const vec3 ambient = vec3(0.2);

const vec3 look = vec3(0., 0., 1.);
const vec3 light = vec3(-5., 5., 5.);
const vec3 light_col = vec3(1.);
const float light_strength = 1.0;
float alpha_depth_func (float x) {
//    return min(1., 1.4 * pow(max(d,0.), 1./6.));
    return 1. + min(x-0.2, 0.0) * 5.;
}
void main()
{
    vec3 col = fcolor * ambient;
    if (!useTexColor) {
        vec4 t = texture2D(texColor, texCoord);
        if (t.a < 0.1) discard;
        col = t.rgb * ambient;
    }
    vec3 normal = normalize(fnormal);
    vec3 light_dir = normalize(light - fposition);
    float diffuse = max(dot(light_dir, normal), 0.);
    float specular = pow(max(dot(look, -reflect(normal, light_dir)), 0.), 16.);
    col += (diffuse * 0.5 + specular * 0.5) * light_col * light_strength;
    outputColor = vec4(col, alpha_depth_func(cameraPosition.z));
}