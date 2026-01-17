def score_decision(predicted, actual):

    if actual > predicted:
        return 9
    if actual == predicted:
        return 7
    return 4
