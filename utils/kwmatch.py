from konoha import WordTokenizer
from typing import List, Dict, Tuple, Set

def get_tokenizer_names(sentence_splits, tokenizer_type: str) -> Set[str]:
    if tokenizer_type == "nagisa":
        skip_tags = ["動詞", "助動詞", "空白", "助詞"]
        return {n.surface for n in sentence_splits if n.postag not in skip_tags}
    return {str(n) for n in sentence_splits}

def find_possible_matches(sentence: str, keyword_list: List[str]) -> Set[str]:
    return {str(k) for k in keyword_list if str(k) in sentence}

def find_positions(sentence: str, possible_matches: Set[str]) -> Dict[int, List[str]]:
    positions_matches = {}
    for m in possible_matches:
        possible_positions = [
            i for i in range(len(sentence)) if sentence.startswith(m, i)
        ]
        for p in possible_positions:
            positions_matches.setdefault(p, []).append(m)
    return positions_matches

def find_overlapping_ranges(
    ranges: List[Tuple[int, int, str]]
) -> List[Tuple[Tuple[int, int, str], Tuple[int, int, str]]]:
    overlapping_ranges = []
    for i in range(len(ranges)):
        for j in range(i + 1, len(ranges)):
            if ranges[j][0] < ranges[i][1]:
                overlapping_ranges.append((ranges[i], ranges[j]))
    return overlapping_ranges

def remove_overlapping_positions(
    positions_matches: Dict[int, List[str]],
    overlapping_ranges: List[Tuple[Tuple[int, int, str], Tuple[int, int, str]]],
) -> None:
    to_remove_range = [
        min(c, key=lambda tup: len(tup[-1]))[0] for c in overlapping_ranges
    ]
    for k in to_remove_range:
        positions_matches.pop(k, None)

def get_unique_candidates(positions_matches: Dict[int, List[str]]) -> List[str]:
    unique_candidates = []
    for v in positions_matches.values():
        if len(v) == 1:
            if v[0] not in unique_candidates:
                unique_candidates.append(v[0])
        else:
            longest = max(v, key=len)
            if longest not in unique_candidates:
                unique_candidates.append(longest)
    return unique_candidates

def filter_candidates(unique_candidates: List[str], names: Set[str]) -> List[str]:
    to_remove = [c for c in unique_candidates if len(c) == 1 and c not in names]
    for c in unique_candidates:
        if c not in to_remove:
            for name in names:
                if c in name and c != name:
                    to_remove.append(c)
                    break
    return [u for u in unique_candidates if u not in to_remove]

def match_keywords(
    sentence: str,
    *,
    keyword_list: List[str],
    tokenizer_type: str = "nagisa",
    **tokenizer_args,
) -> List[str]:
    """Matches keywords in a given sentence using a specified tokenizer.
    Args:
        sentence (str): The input sentence in which to search for keywords.
        keyword_list (List[str]): A list of keywords to match in the sentence.
        tokenizer_type (str, optional): The type of tokenizer to use. Defaults to "nagisa".
        **tokenizer_args: Additional arguments to pass to the tokenizer.
    Returns:
        List[str]: A list of matched keywords found in the sentence.
    """
    tokenizer: WordTokenizer = WordTokenizer(tokenizer_type, **tokenizer_args)

    sentence_splits = tokenizer.tokenize(sentence)
    names = get_tokenizer_names(sentence_splits, tokenizer_type)

    possible_matches = find_possible_matches(sentence, keyword_list)

    positions_matches = find_positions(sentence, possible_matches)
    ranges = sorted(
        [
            (k, k + len(max(v, key=len)) - 1, max(v, key=len))
            for k, v in positions_matches.items()
        ],
        key=lambda x: x[0],
    )
    overlapping_ranges = find_overlapping_ranges(ranges)
    remove_overlapping_positions(positions_matches, overlapping_ranges)
    
    unique_candidates = get_unique_candidates(positions_matches)

    return filter_candidates(unique_candidates, names)
