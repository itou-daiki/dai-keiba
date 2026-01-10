def test_jra_logic(raw_text):
    print(f"Testing JRA Logic with input: '{raw_text}'")
    corner_vals = ['', '', '', '']
    if raw_text:
        parts = raw_text.replace(' ', '-').split('-')
        valid_c = parts[-4:]
        for i, v in enumerate(valid_c):
            if i < 4: corner_vals[i] = v
    print(f"  Result: {corner_vals}")
    return corner_vals

def test_nar_logic(corner_positions_forward):
    print(f"Testing NAR Logic with input: {corner_positions_forward}")
    valid_corners = corner_positions_forward[-4:]
    result = {}
    for j, pos in enumerate(valid_corners):
        result[f'corner_{j+1}'] = pos
    print(f"  Result: {result}")
    return result

if __name__ == "__main__":
    print("--- JRA TESTS ---")
    test_jra_logic("10-10-8-5")       # Standard 4
    test_jra_logic("1-1")             # Short
    test_jra_logic("15-15-14-10-5")   # Long (5)
    
    print("\n--- NAR TESTS ---")
    test_nar_logic(['10', '10', '8', '5'])
    test_nar_logic(['1', '1'])
    test_nar_logic(['15', '15', '14', '10', '5'])
