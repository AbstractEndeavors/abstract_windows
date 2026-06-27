from abstract_utilities import make_list
def get_strings_in_string(string,strings):
    for comp_string in strings:
        if comp_string.lower() in string.lower():
            return True
    return False
def find_longest_common_substring(string, comp_string):
    # Find the longest common substring
    min_len = min(len(string), len(comp_string))
    for length in range(min_len, 0, -1):
        for i in range(len(string) - length + 1):
            substring = string[i:i + length]
            if substring in comp_string:
                return substring
    return None

def get_string_confidence(string,string_remains):
    string_len = len(string)
    remains_str = ''.join(string_remains)
    remains_len = len(remains_str)
    remains_perc = 0
    confidence = 1
    if remains_len:
        remains_perc = remains_len/string_len
        confidence = 1 - remains_perc
    return confidence
def remove_substring(string, substring):
    # Remove the first occurrence of substring and return remaining parts
    idx = string.find(substring)
    if idx == -1:
        return [string]
    remains = [string[:idx], string[idx + len(substring):]]
    return [r for r in remains if r]  # Remove empty strings

def compare_strings(string, comp_string):
    results = []
    
    # Initialize with the original strings
    current_strings = [(string, comp_string)]
    
    while current_strings:
        new_strings = []
        for s, cs in current_strings:
            # Find the longest common substring
            common = find_longest_common_substring(s, cs)
            if not common:
                continue  # No common substring, move to next pair
            
            # Record the found substring and remaining parts
            string_remains = remove_substring(s, common)
            comp_string_remains = remove_substring(cs, common)
            
            # Store the result
            results.append({
                "found": common,
                "string": {"remains": string_remains},
                "comp_string": {"remains": comp_string_remains}
            })
            
            # Add remaining parts for further processing
            for sr in string_remains:
                for csr in comp_string_remains:
                    new_strings.append((sr, csr))
        
        current_strings = new_strings
    string_remains = results[-1].get('string',{}).get('remains')
    string_confidence = get_string_confidence(string,string_remains)
    comp_string_remains = results[-1].get('comp_string',{}).get('remains')
    comp_string_confidence = get_string_confidence(comp_string,comp_string_remains)
    results = {"string":string,
               "comp_string":comp_string,
               "results":results,
               "found":[result['found'] for result in results if result],
               "confidence":{
                   "string":string_confidence,
                   "comp_string":comp_string_confidence
                   }
               }
    return results

def return_best_comp_strings(string, comp_strings):
    results = []
    comp_strings = make_list(comp_strings)
    for comp_string in comp_strings:
        result = compare_strings(string, comp_string)
        results.append(result)
    
    confidence_results = None
    for i, result in enumerate(results):
        confidence = result.get('confidence', {})
        string_confidence = confidence.get('string', 0)
        comp_string_confidence = confidence.get('comp_string', 0)
        if confidence_results is None:
            #if string_confidence>.70:
                confidence_results = [string_confidence, comp_string_confidence, i]
        elif string_confidence > confidence_results[0]:
            confidence_results = [string_confidence, comp_string_confidence, i]
        elif string_confidence == confidence_results[0]:
            if comp_string_confidence > confidence_results[1]:
                confidence_results = [string_confidence, comp_string_confidence, i]
    
    return comp_strings[confidence_results[2]]

