#version 330

layout(location = 0) in vec3 position;
layout(location = 1) in vec3 normal;
layout(location = 2) in vec3 color;
layout(location = 3) in vec2 texcoord;

out vec3 fposition;
out vec3 fnormal;
out vec3 fcolor;
out vec2 texCoord;
out vec4 cameraPosition;

uniform mat4 modelViewMatrix;
uniform mat4 projectionMatrix;
uniform mat4 viewMatrix;

uniform float time;

void main()
{
    fnormal = (modelViewMatrix * vec4(normal, 0.)).xyz;
    fposition = vec3(modelViewMatrix * vec4(position, 1.));
    gl_Position = projectionMatrix * viewMatrix * modelViewMatrix * vec4(position, 1.);
    cameraPosition = gl_Position;
    fcolor = color;
    texCoord = texcoord;
}