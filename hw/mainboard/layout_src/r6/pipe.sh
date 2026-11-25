# pipe.sh : w0 -> s1 (native step 1) -> s2 (Konnect emu) -> s3 (fix stage) + DRC
kp plan_n1.py w0.kicad_pcb n1ops.json | tail -1 && cp w0.kicad_pcb s1.kicad_pcb && kp n1.py s1.kicad_pcb n1ops.json && kp mk_k1.py && cp s1.kicad_pcb s2.kicad_pcb && kp kemu.py s2.kicad_pcb k1ops.json && cp s2.kicad_pcb s3.kicad_pcb && kp fixstage.py s3.kicad_pcb | tail -1 && source drc.sh s3.kicad_pcb s3drc.json
