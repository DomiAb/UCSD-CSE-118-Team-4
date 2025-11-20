# UCSD-CSE-118-Team-4
## SpeechLens
The final project of group 4 for CSE118 Ubiquitous Computing.

# Timeline
| Week  | Tasks | Deadlines | Material |
|-------|-------|-------|-------|
| Week 08 | [Milestone 1](https://github.com/DomiAb/UCSD-CSE-118-Team-4/milestone/1) | Report: 11/20 <br>Presentation: 11/19 <br>Gitlab: 11/20 | [Report](https://sharelatex.tum.de/8788329136gccbwpgzspxq#51f209)<br>[Presentation](https://docs.google.com/presentation/d/108CzD3ogmggYpqZEtp_TaDEwUlDyZr0jnhR-WkWVZiQ/edit?slide=id.p#slide=id.p) |
| Week 09 | [Milestone 2](https://github.com/DomiAb/UCSD-CSE-118-Team-4/milestone/2) | Report: 11/26 <br>Presentation: 11/26 <br>Gitlab: 11/26 | [Report](https://sharelatex.tum.de/3335323536zmcvdmvqnmdd#66005f)<br>[Presentation](https://docs.google.com/presentation/d/1Z2uGD7OuSasZ4JkmUw_P1fbPbgr1T-7093BwPvt2sE0/edit?usp=sharing) |
| Week 10 | [Milestone 3](https://github.com/DomiAb/UCSD-CSE-118-Team-4/milestone/3) | Report: 12/04 <br>Presentation: 12/03 <br>Gitlab: 12/04 | [Report](https://sharelatex.tum.de/7422448739cfvtjqzmvmcb#c4d42e)<br>[Presentation](https://docs.google.com/presentation/d/1yCIHYUiI_1jtA8aglc_Y7q7aCig6smg_pd7AzBBb3k0/edit?usp=sharing) |
| Final Week | [Milestone 4](https://github.com/DomiAb/UCSD-CSE-118-Team-4/milestone/4) | TBC | [Final Presentation](https://docs.google.com/presentation/d/14MlA6kG7u3t0sl2jZDdnlKYao92cdsQxzW0FoPhALRw/edit?usp=sharing)<br>[Final Report](https://sharelatex.tum.de/7636793384dxdqryvycsph#a89a4e)|

# Additional Material
[Project Proposal Report](https://sharelatex.tum.de/project/690d301212fba3742783ac4e)  
[Project Proposal Presentation](https://docs.google.com/presentation/d/199U9tzib8zMWN0UVl53Fl3ZVSA91Sav9CxOjo6CdL8U/edit?slide=id.p#slide=id.p) 

# Setup
## Jetson
Start by creating a virtual environment (one called ```jetson_venv``` is already included in the .gitignore).  
```python3 -m venv jetson_venv```  

Activate this virtual environment.  
```source ./jetson_venv/bin/activate```   

Install the requirements.  
```pip install -r ./jetson/requirements.txt```  

Run the server.  
```python ./jetson/server/main.py```

## HoloLens

# Adresses
IP Address of the Jetson in the class network (```3219```) should be static and is ```192.168.0.249```  
IP Address of the Hololens in the class network (```3219```) is ```192.168.0.192```

# Contributors
Dominik Abel (Dominik.Abel@tum.de)  
Anchit Kumar  
Matthew Williams  
