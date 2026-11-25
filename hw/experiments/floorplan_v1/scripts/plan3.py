# Floor plan v1, arrangement W (KiCad coords: X = encl X + 150, Y = 100 - encl Y; rear edge Y 75, front Y 121)
XR = 238.2         # right edge = antenna boundary of U101 (antenna fully overhangs, Espressif Fig.23 (4))
YR, YF = 75.0, 121.0
AL = 121.3         # AMP_L left edge; amps meet at X 150 under the USB-C
EM = 0.6          # block copper to board edge
XL = AL - 25.3 - EM  # left column = CHG width
OUTLINE = [(XL, YR), (143, YR), (143, 73.5), (157, 73.5), (157, YR), (XR, YR), (XR, YF), (XL, YF)]
PLANE_OUTLINE = [(XL + .3, YR + .3), (XR - 2.3, YR + .3), (XR - 2.3, 100.5), (XR - .3, 100.5), (XR - .3, YF - .3), (XL + .3, YF - .3)]
BBOX = (XL - 3, 70, XR + 8, 124); OUTLINE_BOX = (XL, YR, XR, YF)
BOTTOM_FIDS = ['FID4', 'FID5', 'FID6']; EDGE_MARGIN = 0.2
CLIP_BOOST_PVDD = (114, 86.9, 139.5, 119)
HMAP_TOP, HMAP_BOT = 'hmap_top', 'hmap_bot'
HEIGHT = {'CP_Elec_10x10': 10.5, 'JST_VH_B2P-VH_1x02_P3.96mm_Vertical': 11.5, 'AMASS_XT30PW-M_1x02_P2.50mm_Horizontal': 8.5,
          'JST_XH_B3B-XH-A_1x03_P2.50mm_Vertical': 7.0, 'JST_PH_B2B-PH-K_1x02_P2.00mm_Vertical': 6.0, 'CP_Elec_6.3x5.7': 5.8,
          'PinHeader_1x05_P2.54mm_Vertical': 8.5, 'SW_Push_1P1T_XKB_TS-1187A': 1.6, 'SOIC-16_3.9x9.9mm_P1.27mm': 1.75,
          'ESP32-WROVER-E': 3.3, 'USB_C_Receptacle_HRO_TYPE-C-31-M-12': 3.3, 'L_Changjiang_FXL1040': 4.0,
          'L_Changjiang_FXL0630': 3.0, 'L_Changjiang_FXL0420': 2.0, 'Fuse_2410_6125Metric': 2.7}
# blocks: (deg, align, x, y) -> rotated box corner at (x, y)
BLOCKS = {
    'BATT':  (180, 'tl', XL + EM, YR + EM),            # J801 opening -X at the left board edge
    'CHG':   (0, 'bl', XL + EM, YF - EM),              # front, under the woofer-L basket (low parts only)
    'AMP_L': (90, 'tl', AL, 84.5),                 # outputs to the front (VH), I2S side to the rear corridor
    'AMP_R': (-90, 'tl', 150.5, 84.5),
    'BOOST': (0, 'bl', 179.3, YF - EM),           # VIN at the front edge, C_OUT/PVDD at the rear, L901 front
    'BUCK':  (0, 'tl', 179.0, YR + EM),
}
FIXED = {
    'U101': (XR - 9.395, YF - 10.11, 270, 'F'),
    'J501': (XR - 14.04, 79.6, 180, 'F'),
    'J601': (150.0, 76.67, 180, 'F'),
    'C920': (199.9 + 6.3, 84.6 + 5.44, 0, 'F'),
    'C401': (199.9 + 6.3, 84.6 + 10.9 + 5.44, 0, 'F'),
    'C301': (199.9 + 6.3, 84.6 + 21.8 + 5.44, 0, 'F'),
    'J301': (131.2 + 2.5, YF - 0.2 - 5.34, 0, 'F'),
    'J302': (131.2 + 9.0 + 2.5, YF - 0.2 - 5.34, 0, 'F'),
    'J401': (151.0 + 2.5, YF - 0.2 - 5.34, 0, 'F'),
    'J402': (151.0 + 9.0 + 2.5, YF - 0.2 - 5.34, 0, 'F'),
}
DELETE = ['H6']
KEEPOUT = {'F': [(XR - 2.0, 100.5, XR, YF)], 'B': [(XR - 2.0, 100.5, XR, YF)]}
RULE_AREAS = {'ANT_KEEPOUT': [(XR - 2.0, 100.6), (XR, 100.6), (XR, YF), (XR - 2.0, YF)]}
PLANES = [('GND', 'In1_Cu', 'L2_GND'), ('GND', 'In4_Cu', 'L5_GND')]
GAPPAD_REFS = ['U301', 'U401', 'U701']; GAPPAD = 15.0

R2 = (0, 90); R4 = (0, 90, 180, 270)
TPG = (XL, YR, 2.54)
GROUPS = [
    (['H1'], 'F', (XL + 3.6, YR + 3.6), (0,), 30), (['H2'], 'F', (140.0, 78.6), (0,), 20), (['H3'], 'F', (XR - 3.6, 98.0), (0,), 20),
    (['H4'], 'F', (174.0, YF - 3.6), (0,), 20), (['H5'], 'F', (125.0, YF - 3.6), (0,), 20),
    (['U501'], 'F', (219.0, 92.0), R2, 15), (['J502'], 'F', (226.0, 92.0), R4, 25),
    (['U201'], 'F', (139.0, 80.0), (90, 0), 14), (['C201'], 'B', ('U201', '16'), R2, 4),
    (['J802'], 'F', (118.0, 92.0), R4, 30), (['J803'], 'F', (118.0, 80.0), R4, 30),
    # USB-C input: TVS at the connector, ESD, bulk
    (['D601'], 'F', (153.5, 84.0), R2, 8), (['U601'], 'F', (146.5, 84.0), R2, 8), (['U602'], 'F', (155.5, 82.5), R2, 8),
    (['C605'], 'F', (159.0, 79.0), R2, 12), (['C604', 'C601'], 'F', (155.5, 84.0), R2, 8),
    (['R601', 'C602'], 'F', (157.0, 84.0), R2, 10),
    (['U603', 'R602', 'Q601', 'Q602', 'R603', 'R604'], 'F', (163.0, 80.0), R2, 14),
    (['Q201', 'Q202', 'R201', 'R202', 'R203', 'R204'], 'F', ('U201', None), R2, 14),
    # MCU support (MCU column + right corridor)
    (['C101', 'C102'], 'B', ('U101', '2'), R2, 5), (['C103'], 'B', ('U101', '3'), R2, 5),
    (['R110', 'R111', 'R112', 'R113', 'R114', 'R115', 'R116', 'R117', 'R118'], 'F', (222.0, 98.0), R2, 14),
    (['R501', 'R502', 'R503', 'R504', 'C104'], 'F', (230.0, 87.0), R2, 14),
    (['SW101'], 'F', (232.0, 95.0), R2, 16), (['SW102'], 'F', (205.0, 79.5), R2, 40),
    (['R101', 'R102', 'R103', 'D101', 'R104', 'R105', 'R106', 'R107', 'R108', 'R109'], 'F', (228.0, 98.0), R2, 18),
    (['Q101', 'Q102', 'R119', 'R120', 'R121', 'R122'], 'F', (214.0, 98.0), R2, 16),
    (['C501', 'C502', 'C503'], 'B', ('U501', '16'), R2, 5),
    (['R505', 'R506', 'R507', 'R508', 'R509', 'R510', 'R511'], 'F', ('U501', None), R2, 15),
    (['R301'], 'F', ('U301', None), R2, 18), (['R401'], 'F', ('U401', None), R2, 18),
    (['D901', 'C917', 'C918', 'R908', 'R909'], 'F', ('U901', None, 0, -6), R2, 16),
    (['R701', 'R702', 'R703', 'R704', 'R705', 'R706', 'R707', 'R708', 'R710', 'R709', 'C719', 'C720', 'C721', 'D701'], 'F', ('U701', None), R2, 16),
    (['SW701'], 'F', (190.0, 88.0), R2, 80),
    (['D951', 'R956'], 'F', ('U951', None), R2, 14),
    (['U801', 'C801', 'C802', 'C803', 'R801', 'R802', 'R811', 'R810'], 'F', (118.0, 92.0), R2, 22),
    (['U802', 'Q803', 'C804', 'R804', 'R805', 'R806', 'U803', 'Q804', 'C805', 'R807', 'R808', 'R809'], 'F', (118.0, 88.0), R2, 45),
    (['JP801', 'JP802', 'JP803', 'TH801'], 'F', (118.0, 86.0), R2, 70),
    (['C603'], 'F', ('U601', None), R2, 6),
    (['FID1'], 'F', (XL + 1.5, YR + 1.5), (0,), 60), (['FID4'], 'B', (XL + 2, YR + 6), (0,), 40), (['FID5'], 'B', (XR - 4, YR + 12), (0,), 40), (['FID6'], 'B', (176.0, YF - 2), (0,), 40), (['FID2'], 'F', (XR - 1.5, 98.5), (0,), 25), (['FID3'], 'F', (176.0, YF - 1.5), (0,), 25),
    # test points: bottom, 2.54 mm grid
    (['TP101', 'TP102', 'TP103', 'TP104', 'TP105', 'TP106', 'TP107', 'TP108', 'TP109', 'TP110'], 'B', (222.0, 92.0), (0,), 25, TPG),
    (['TP301', 'TP302', 'TP303', 'TP305'], 'B', ('U301', None, 0, -9), (0,), 20, TPG),
    (['TP304'], 'B', ('U301', None, -9, 0), (0,), 20, TPG), (['TP401'], 'B', ('U401', None, 9, 0), (0,), 20, TPG),
    (['TP601', 'TP602'], 'B', (152.0, 86.0), (0,), 20, TPG),
    (['TP701', 'TP702', 'TP703'], 'B', ('U701', None, 0, -10), (0,), 20, TPG),
    (['TP801', 'TP802', 'TP803'], 'B', (110.0, 92.0), (0,), 20, TPG),
    (['TP901', 'TP952'], 'B', ('U901', None, 0, -8), (0,), 20, TPG),
    (['TP951', 'TP953', 'TP954'], 'B', ('U951', None), (0,), 20, TPG),
]
