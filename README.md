# CARLA-Modified-Pipeline
For ECE499: Senior Thesis at UIUC. Modified from the 2020 CARLA Challenge.

![Original Friction](./(ECE499)%20Deliverables/Motivation%20Example/Motivation%20Example%20GIF/orig%20fric%20-%20clear_sunset_icy_70_ghost_cutin.gif)

![Modified Friction](./(ECE499)%20Deliverables/Motivation%20Example/Motivation%20Example%20GIF/reduced%20fric%20-%20clear_sunset_icy_70_ghost_cutin.gif)

### Problem Statement
The challenge lies in the safety of autonomous vehicles (AVs), as current simulators like CARLA may not effectively simulate crucial aspects, particularly in challenging weather conditions. The thesis aims to enhance CARLA by introducing friction to actor vehicles in adverse scenarios like rain and ice. The evaluation suggests that these modifications could significantly impact accident rates, emphasizing the need for improved and more accurate simulation tools to ensure safer development of AVs.

The thesis indicates that in adverse scenarios, the modifications to CARLA's simulation could increase the accident rate from 49% to 98% compared to the existing implementation. This substantial rise in the accident rate highlights the potential dangers and unintended outcomes that may arise from inadequate simulation of challenging conditions, emphasizing the importance of enhancing simulation tools for autonomous vehicle development.

### Folder Descriptions
- `./(ECE499) Deliverables` includes the thesis and presentation at the ECE Symposium 2023 along with visualizations.
- `./campaign_configs` includes weather specifications and parameters.  
- `./(ECE499) Simulations` includes data generated from different scenarios from weather parameters with and without friction modification. The scenarios used are:
    - Ghost Cut-in
    - Lead Cut-in
    - Lead Slowdown
- `./(ECE499) Evaluation` includes scripts for data processing.

### Modification Explanation
- Ghost Cut-in Sequence ![Ghost Cut-in Sequence](./(ECE499)%20Deliverables/Ghost%20Cutin%20Sequence.png)

- Scenario modification sequence: ![Flowchart](./(ECE499)%20Deliverables/Flowchart.png)

A weather parameter is passed into the scenario so that the friction of a vehicle can be determined when spawned based on a known formula. 

### Installation
Please refer to the [source repo](https://github.com/bradyz/2020_CARLA_challenge) and `./(ECE499) Environment Setup`.

