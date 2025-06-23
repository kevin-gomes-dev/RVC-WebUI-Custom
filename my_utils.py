# Find the first sentence in text. Considers "test...this." to be one sentence, and "test... However." to be 2 and will return "test..."
def get_first_sentence(text_input):
    text = text_input
    sentence = ''
    endings = ['!','?','.']
    for i,char in enumerate(text):
        sentence += char
        if char in endings:
            # We're done if the char we're at is the last one
            if i+1 == len(text):
                return sentence
            else:
                # If the next char is a space, sentence ended.
                if text[i+1] == ' ':
                    return sentence
    return sentence
        
# Get a list of sentences from the text.
def get_sentences(text_input) -> list[str]:
    text = text_input
    sentences = []
    try:
        while text:
            sen = get_first_sentence(text)
            sentences.append(sen)
            sen_index = text.find(sen)
            text = text[:sen_index] + text[sen_index + len(sen):]
            text = text.strip()
    except:
        print('Something went wrong trying to get length of sentences.')
        raise
    return sentences

# Get a list of sentences from the text limited by some limit. If limit is too small, use the longest sentence length. If limit is <= 0, just get a list of 1 item being the entire line
def get_limited_sentences(text_input,limit = 0) -> list[str]:
    text = text_input
    if limit <= 0:
        return [' '.join(get_sentences(text))]
    sentences = get_sentences(text)
    items = []
    min_limit = max(map(lambda x : len(x),sentences))
    # Use longest sentence if bad limit given
    if not limit or limit < min_limit:
        limit = min_limit
    # Store current length. If exceed, reset and add new item.
    current_length = 0
    # Store the current item
    current_item = ''
    # Store the ever growing string. Once we reach limit, reset this.
    s = ''
    while len(sentences) > 0:
        current_item = sentences.pop(0) + ' '
        s += current_item
        current_length += len(current_item)
        # If we are at last item, append whatever we have
        if len(sentences) == 0:
            items.append(s.rstrip())
        # Check the next item's length to the current. If it exceeds the limit, append what we have and start fresh.
        elif current_length + len(sentences[0]) > limit:
            items.append(s.rstrip())
            current_item = ''
            s = ''
            current_length = 0
    return items