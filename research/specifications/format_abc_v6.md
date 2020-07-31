# Lithtech ABC v6

The ABC format is a common 3d model format used in many early Lithtech games. This document covers the specifications for ABC version 6, which is the main format for Lithtech 1.0 - 1.5.

A few important notes, texture names aren't stored in this file. They are mostly the same name as the model, and stored under `<root>/Skins/` instead of `<root>/Models/`. You can find exact references in each game's source code (if that's available.) 

This file is little-endian.

This document and reverse engineering effort is based off the [original specification document](https://web.archive.org/web/20080605043643/http://bop-mod.com/download/docs/LithTech-ABC-v6-File-Format.html) by Allan "Geist" Campbell. 

## Helper Structs

Before we begin, here's a few helper structs that you'll see throughout the document.

``` c++
struct LTString {
    short Length;
    char Value[Length];
};

struct LTNormal {
    char x,y,z;
};

struct LTUVPair {
    float u,v;
};

struct LTVector {
    float x,y,z;
};

struct LTRotation {
    float x,y,z,w;
};
```

## Sections

``` c++
struct Section {
    LTString SectionName;
    uint NextSectionLocation;
};
```

Each part of the model is separated into friendly little sections. It holds the name of the data that's about to be laid out, and the next section's location in bytes from the beginning of the file. If it's the last section in the file, the value will be `0xFFFFFFFF`.

The exact `SectionName` will be declared in each structure throughout the document.

## Header


``` c++
LTString SectionName = 'Header';

struct Header {
    LTString FileToken;
    LTString CommandString;
};
```

For ABC v6 models, the `FileToken` is always `MonolithExport Model File v6`. `CommandString` is generally empty, although it's used when the model needs to share some meta-data with the engine. These commands are not known at this time.

## Geometry
``` c++
LTString SectionName = 'Geometry';

struct Triangle {
    LTUVPair TexCoords1;
    LTUVPair TexCoords2;
    LTUVPair TexCoords3;
    ushort VertexIndex1;
    ushort VertexIndex2;
    ushort VertexIndex3;
    LTNormal FaceNormal;
};

struct Vertex {
    LTVector Position;
    LTNormal VertexNormal;
    uchar TransformationIndex;
    ushort Replacements[2];
};

struct Geometry {
    LTVector BoundsMin;
    LTVector BoundsMax;
    uint NumLODS;
    ushort VertexStartNum[NumLODS+1];
    uint NumTris;
    Triangle FaceInfo[NumTris];
    uint NumVerts;
    uint NormalVerts;
    Vertex VertexInfo[NumVerts];
};
```

Geometry is rather straightforward. VertexInfo is filled with level of detail (LOD) meshes starting with the lowest level, moving its way up. These LODs are indexed by `VertexStartNum`. Use this info to iterate through `VertexInfo`. To simply grab the original mesh, use the last value in `VertexStartNum`. Similarly `NumVerts` refers to the entire mesh's vertice count including LODs. The original mesh's vertex count is the `NormalVerts` value.

It is currently unknown how to determine which LOD vertex uses which face. For the original mesh, you can freely use the face data from the beginning.

The bounding boxes (`BoundsMin` and `BoundsMax`) are most likely used for either collision or visibility detection. 

For ABC v6 a vertex can only be assigned to one node at a time. This is indicated by the `TransformationIndex` property.

Geometry is stored in object space, and must be transformed into world space using the first frame of the first animation (This includes vertex animated meshes.)

## Nodes
``` c++
LTString SectionName = 'Nodes';

struct Node {
    LTVector BoundsMin;
    LTVector BoundsMax;
    LTString NodeName;
    ushort TransformationIndex;
    uchar Flags;
    uint NumMDVerts;
    ushort MDVertList[NumMDVerts];
    uint NumChildren;
};

enum NodeFlags {
    Null = 1,
    Triangles = 2,
    Deformation = 4,

    // The following might be exclusive to Lithtech 1.5
    EnvironmentMap = 8,
    EnvironmentMapOnly = 16,
    ScrollTextureU = 32,
    ScrollTextureV = 64,
};
```

Nodes are essentially bones for the mesh. They can be used to provide skeletal-based animations, or be an indicator for vertex animations. Nodes with the `Null` flag are simply hierarchical in nature and prove no real purpose. The first node is known as the root node and is always `Null`. 

The `TransformationIndex` is the node's ID. Each vertex in the geometry section references at least one node.

If a node has the `Deformation` flag set, `NumMDVerts` will be greater than 0, and `MDVertList` will contain vertex indexes. Which will be used later on in the animation section.

Nodes are stored in depth first order. So you simply need to traverse each node's `NumChildren` amount. 

The bounding boxes (`BoundsMin` and `BoundsMax`) are most likely used for either collision or visibility detection. 

## Animations
``` c++
LTString SectionName = 'Animation';

struct NodeDeformationFrame {
    uchar Position[3];
};

struct NodeKeyFrame {
    LTVector Translation;
    LTRotation Rotation;
};

struct KeyFrameInfo {
    uint TimeIndex;
    LTVector BoundsMin;
    LTVector BoundsMax;
    LTString FrameString;
};

struct AnimInfo {
    LTString AnimName;
    uint Length;
    LTVector BoundsMin;
    LTVector BoundsMax;
    uint NumKeyframers;
    KeyFrameInfo KeyframeData[NumKeyframers];
};

// Pseudo code adapted from my 010 Editor binary template
void ReadAnimations(FileHandle* File, uint NumNodes, Node* Nodes)
{
    // Animation count
    uint NumAnims << File;

    for (int AnimIndex = 0; AnimIndex < NumAnims; AnimIndex++)
    {
        // Basic info about the animation
        AnimInfo Info << File;

        for (int NodeIndex = 0; NodeIndex < NumNodes; NodeIndex++)
        {
            // Number of keyframes in this animation
            uint NumKeyFramers = Info[AnimIndex].NumKeyframers;

            // Vertex animation vertex count
            NumMDVerts = Nodes[NodeIndex].NumMDVerts;

            bool HasMDVerts = NumMDVerts > 0;

            // Mostly skeletal based information on the keyframe
            NodeKeyFrame NodeKeyFrameData[NumKeyFramers] << File;

            // If there's vertex animations in this node, then the location data for each frame will be stored here
            if (HasMDVerts)
            {
                // Note, these are compressed location values, we'll need to process them first!
                // This goes for the length of mesh deformation vertices, and keyframes.
                NodeDeformationFrame VertexAnimation[NumMDVerts * NumKeyframers] << File;
            }

            // Only used for deformation nodes, otherwise (1,1,1) and (0,0,0) respectively.
            LTVector Scale << File;
            LTVector Transform << File;

            // Let's process any vertex animations!
            if (HasMDVerts)
            {
                for (int MDVertIndex = 0; MDVertIndex < count(VertexAnimation); MDVertIndex++)
                {
                    // Retrieve the our unprocessed vertex animations!
                    LTVector Deformation = VertexAnimation[MDVertIndex]

                    // Apply scale and transform
                    Deformation.x = (Deformation.x * Scale.x) + Transform.x
                    Deformation.y = (Deformation.y * Scale.y) + Transform.y
                    Deformation.z = (Deformation.z * Scale.z) + Transform.z

                    // Apply our uncompressed vertex animation
                    VertexAnimation[MDVertIndex] = Deformation;
                }
            }
        }
    }
}
```

Animations can be skeletal or vertex based. Due to the complexity, I've included a commented pseudo read animation function that should be useful. `<< File` will read the file for the length of the file type it's going into.  

There's a few things to note here. `KeyFrameInfo.FrameString` is another meta-data command for the engine. An example of a command would be to play a sound using `SOUND_KEY squeakytoy\idle1` during a specific frame. Or to note when a foot is against the floor to play a footstep sound or play an effect.

Vertex animations are stored compressed. Much like Quake 2's MD2 format, you need to apply the Scale and Transform to get the proper location data.

## Animation Dims
``` c++
LTString SectionName = 'AnimDims';

void ReadAnimationDims(uint NumAnims)
{
    LTVector Dimensions[NumAnims];
}
```

Not much is known about AnimationDims other than the structure.

## Transform Information
``` c++
LTString SectionName = 'TransformInfo';

struct TransformInfo {
    int FlipMat;
    int FixAnimKeyframes;
};
```

This section only appears in Lithtech 1.5 games, and I haven't exactly 100% determined the purpose flags. It appears `FlipMat` will flip the Z axis of the matrix. `FixAnimKeyframes` is a bit of a mystery but by using a quaternion conjugate function it corrects odd rotations found in Lithtech 1.0 models.

While this section is left out in Lithtech 1.0 models, Lithtech 1.5 games account for this section missing by defaulting both flags to `1`.

## Triangle Strips
``` c++
LTString SectionName = 'TriStrips';
```
This section name was found while reverse engineering. Nothing else is known.