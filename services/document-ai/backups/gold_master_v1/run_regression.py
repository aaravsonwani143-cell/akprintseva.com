import cv2, json, os, numpy as np, sys
sys.path.insert(0, 'c:/Users/win11/.gemini/antigravity-ide/scratch/public_html/services/document-ai')
from aadhaar_processor import process_aadhaar_pipeline, classify_image_type

test_suite = [
    ('Keyboard Tilted', 'C:/Users/win11/.gemini/antigravity-ide/brain/2b3c0361-b644-42e5-a37e-de5c912b2225/.user_uploaded/media_1788505913610.jpg', 'front', 'dark_bg_mixed', 'regression_Keyboard_Tilted.jpg'),
    ('Soil/Mud', 'C:/Users/win11/.gemini/antigravity-ide/brain/2b3c0361-b644-42e5-a37e-de5c912b2225/.user_uploaded/media_1788465429844.jpg', 'back', 'granular_ground', 'regression_Soil_Mud.jpg'),
    ('Laminated Dark Floor', 'C:/Users/win11/.gemini/antigravity-ide/brain/2b3c0361-b644-42e5-a37e-de5c912b2225/.user_uploaded/media_1788460003175.jpg', 'back', 'dark_bg_mixed', 'regression_Laminated_Dark_Floor.jpg'),
    ('Fabric Bedsheet', 'C:/Users/win11/.gemini/antigravity-ide/brain/2b3c0361-b644-42e5-a37e-de5c912b2225/.user_uploaded/media_1788455702896.jpg', 'front', 'dark_bg_mixed', 'regression_Fabric_Bedsheet.jpg'),
    ('Solid Red', 'C:/Users/win11/.gemini/antigravity-ide/brain/2b3c0361-b644-42e5-a37e-de5c912b2225/.user_uploaded/media_1788427160029.jpg', 'front', 'solid_color', 'regression_Solid_Red.jpg'),
    ('Plastic Folder (NEW)', 'C:/Users/win11/.gemini/antigravity-ide/brain/2b3c0361-b644-42e5-a37e-de5c912b2225/.user_uploaded/media_1788507589679.png', 'front', 'plastic_folder', None),
]

all_pass = True
print('='*80)
print('COMPREHENSIVE 6-SURFACE VERIFICATION SUITE')
print('='*80)

for name, path, exp_side, exp_type, baseline_file in test_suite:
    safe_name = name.replace(' ', '_').replace('/', '_').replace('(', '').replace(')', '')
    img = cv2.imread(path)
    cl = classify_image_type(img)
    out_p = 'C:/Users/win11/.gemini/antigravity-ide/brain/2b3c0361-b644-42e5-a37e-de5c912b2225/scratch/regression_final_' + safe_name + '.jpg'
    res = process_aadhaar_pipeline(path, out_p)
    
    out_img = cv2.imread(out_p)
    oh, ow = out_img.shape[:2]
    
    type_ok = (cl['type'] == exp_type)
    side_ok = (res['side'] == exp_side)
    size_ok = (ow == 1014 and oh == 638)
    
    diff_ok = True
    if baseline_file:
        base_path = 'C:/Users/win11/.gemini/antigravity-ide/brain/2b3c0361-b644-42e5-a37e-de5c912b2225/scratch/' + baseline_file
        if os.path.exists(base_path):
            base_img = cv2.imread(base_path)
            diff = np.max(np.abs(out_img.astype('float32') - base_img.astype('float32')))
            diff_ok = (diff == 0.0)
            diff_str = f"Diff={diff:.1f}"
        else:
            diff_str = "NoBaseline"
    else:
        out_lab = cv2.cvtColor(out_img, cv2.COLOR_BGR2LAB)
        min_edge = min([
            float(np.mean(out_lab[:10, :, 0])),
            float(np.mean(out_lab[-10:, :, 0])),
            float(np.mean(out_lab[:, :10, 0])),
            float(np.mean(out_lab[:, -10:, 0]))
        ])
        diff_ok = (min_edge > 155.0)
        diff_str = f"EdgeL={min_edge:.1f}"

    passed = type_ok and side_ok and size_ok and diff_ok
    if not passed:
        all_pass = False
        
    status = 'PASS' if passed else 'FAIL'
    slot_str = 'Slot 1' if res['side'] == 'front' else 'Slot 2'
    c_type = cl['type']
    r_side = res['side']
    print(f"[{status}] {name:22s}: Cl={c_type:16s} Side={r_side:5s} ({slot_str}) Size={ow}x{oh} {diff_str}")

print('='*80)
if all_pass:
    print('OVERALL RESULT: ALL 6 TESTS PASSED! ZERO REGRESSION!')
else:
    print('OVERALL RESULT: SOME TESTS FAILED!')
print('='*80)
