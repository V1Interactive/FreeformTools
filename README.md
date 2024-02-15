# freeform-tools
- Beta Tutorials - https://www.youtube.com/channel/UCHXLfl9y2os_gvCzhR7UFlQ
- User Documentation - https://sites.google.com/view/v1freeformtools/home
- Installation - https://sites.google.com/view/v1freeformtools/installation

For Maya 2022.x and 2023.x using Python 3.9

Home of an open source freeform rigging and animation toolset for Maya, made for games development.  These tools are built 
off of my experience working with animators that wanted flexibility in their rigs so that they could animate how they wanted
and have the rig respond to their work rather than dictate how they work.

All of the rigging made with this system is editable at anytime during animation and the tools are built to preserve
all animation as the rig changes.  Building the toolset with this in mind lets the rigging systems become an animator tool
rather than a technical artist tool that builds rigs to be handed off to animation.  It also means that the rig can change to 
fit one off animation needs without creating an interation cycle between technical art and animation.

The base of this toolset was developed for V1 Interactive and has been built to support a full studio pipeline.  However,
I believe it's simple enough that animators of any skill level will be able to pick it up and build rigs for any characters.


The code in this project is a mix of C# and Python.  All UI is made with XAML in C# with Python using Python.NET to work with the C#
tools.  Python launches all UI and registers methods onto C# events so that the C# UI can call Python code in Maya.
I've chosen this mix because of the power and ease of making data driven UI following a MVVM(Model-View-ViewModel) code pattern using XAML.
As well as the flexibility of having a UI system that will work in any Python environment.  Following this pattern 1 UI can be
used in Maya, 3DS Max, and any other Python environment, with each program loading their specific functionality onto the C# UI events.



## Project Pillars

This project is guided by a few development pillars.

- Skeleton keyframes are the definitive source of animation
- Rigs are a tool of animation and shouldn't limit work
- Data driven tools



## Toolset Breakdown

#### Metadata/Metanode System 
A full metadata network system for saving code state in Maya scenes and easy rig searchability.

The metadata network is a tree-structure of Maya network nodes that use wired connections to form scene relationships
between complex groups of objects.  This keeps the entire structure object name agnostic and allows quick traversal up
and down the tree to find characters and pieces of the rig progmatically.


#### Modular component based rigging
The rigging system is based on a skeleton markup system that lets the user define different regions of the skeleton.  
The system reads in these regions and allows rigging of them.  For example, the user can define the 'arm' as the joint
chain from the shoulder to the wrist.  The rig system will read in the start and end joint and find the chain of joints
between them to apply rigging to.

There are 2 parts to the rig system.  Rigging Components, which are your different rig options, such as FK and IK.  And
Overdrivers, which are a constraint system between rig controls.  A full rig is made by building different regions as FK
and IK, and then using Overdrivers to create more complex relationships.
For example, a human leg with a reverse foot setup would create an IK rig from the thigh to the ankle, and a reverse foot 
from the ankle to the heel.  Then you would use an overdriver to connect the leg IK control to the ankle joint of the reverse
foot rig component so that the foot setup drives the IK control.

The Overdriver system also doubles as the space switching system for the rigs.  At any point the animator can Overdrive any
rig control object by almost any other object in the scene, which will bake the existing animation into the new space.
Any overdriven relationship that creates a cycle in Maya will result in Maya

As a more advanced feature, multiple rigs can be applied to a single region to create some more familiar setups like an
IK/FK switchable arm.  The default tools IK/FK switching behavior removes the existing component and replaces it with the switch.
Multiple spaces can also be set on a rig control with the ability to key switches between each space.

All rigging is constructed off of the zero pose of the character on world origin in order to ensure consistency when
building the rigs on characters who's animation may be offset.


#### Modular Exporter
The built in exporter works with the same skeleton markup as the rigging.  When a character is first setup the rig system
will tag basic properties onto all joints, such as whether or not they should export.  Just like the rigger the exporter is
reactive to properties that are either on joints or on the export assets themselves.  

Specific joints can be tagged to remove animation so that we can visualize game engine dynamic systems on joints, but not 
introduce keyframes that would interfere in engine.  Characters can also be exported from world origin no matter where the 
animation is placed in the scene.  Properties could be made to modify joints or full characters in just about any way.

All export properties only act on a duplicate of the skeleton that is baked from the existing character animation, so that
the export process never modifies your character animation.


#### Perforce Integration
To fit studio needs, the tools come with Perforce integrations using the C# Perforce API. Test
