# Need to add speaker wavs, model and index names in order to run. For files, presumes each set of lines to be:

# <Speaker><Emotion>
# Text

# For example:
# JA
# I'm John, and I'm angry

# Speakers we will use, so we can shorten text gen
# ...

# For RVC
# ...

# Change to generate different
speaker_dict = {}
speakers = {}
root_speaker_wav_path = 'speakers'

import time
import os

import itertools
from my_utils import get_limited_sentences
import subprocess

# Print my downloaded models
models = {"m": "tts_models/multilingual/multi-dataset/xtts_v2",
          "j": "tts_models/ja/kokoro/tacotron2-DDC",
          "y": "tts_models/multilingual/multi-dataset/your_tts"}
d = input('Skip loading model? Anything for yes, nothing for no: ')
# d = False
device = "cuda"
if not d:
    from TTS.api import TTS
    model = models["m"]
    tts: TTS = TTS((model), progress_bar=True).to(device)

print("Downloaded models:\n",models)

def sanitize(raw_data):
    """
    Takes raw data and adds in any empties missing, changing them to default values for parameter setup.
    Order expected is: speaker_wav(s) (or name),|text_prompt,|language,|emotion,|speed,|split_sentences
    
    Returns:
        data: The data to use for tts parameters.
    """
    data = (raw_data.split(",|"))
    for i in range(len(data)):
        data[i] = data[i].strip()
    while len(data) < 6:
        data.append(None)
    # print("Raw data, blanks replaced with None:",data)
    
    # Separate into vars for easier reading
    if len(data[0]) < 5:
        if data[0] not in speakers:
            print(str(data[0]) + " is invalid speaker. Defaulting to 'Z'. Rest of info: " + str(data))
            speaker_wav = speakers["Z"]
        else:
            speaker_wav = speakers[data[0]]
    else:
        speaker_wav = data[0].split(",")
    text = data[1]
    lang = data[2] or "en"
    emo = data[3] or "Neutral"
    speed = data[4] or 1.0
    split = data[5] or False
    data = [speaker_wav,text,lang,emo,speed,split]
    # print("Using data:",data)
    return data

# Prefix the root path to each file name
for k,v in speakers.items():
    new_speakers = []
    for file in v:
        new_speakers.append(os.path.join(root_speaker_wav_path,file))
    speakers[k] = new_speakers
print(speakers)


emotions = {
    "A": "Angry",
    "S": "Sad",
    "H": "Happy",
    "N": "Neutral"
}

# Type in own generations
def custom(count = 1):
    # Do forever unless you type q to stop, main program
    while True:
        # How many lines to make
        gen_lines = []
        raw_data = ""
        print("For multiple wavs, separate with ',' For starting generations, blank return or type 'd'. Type in 'q' to go back to define count.")
        print("Input can be 2 formats. speaker1.wav,speaker2.wav,|TEXT,|LANG,|EMO,|SPD,|SPLIT")
        raw_lines = []
        while True:
            # if len(gen_lines) >= 10:
            #     print("Amount of lines to generate is 10 or higher. Generating now to avoid filename issues.")
            #     break
            raw_data = input("\nEnter all data in the order of: speaker_wav(s) (or name),|text_prompt,|language,|emotion,|speed,|split_sentences.\n")
            if (raw_data == "d" or raw_data == "q" or raw_data == ""):
                break
            raw_lines.append(raw_data)
            # print("\nRaw data:",raw_data)
            gen_lines.append(sanitize(raw_data))
        # End main loop, exit program
        if raw_data == "q" or raw_data =="'q'":
            print("Quitting...")
            break
        else:
            if len(gen_lines) <= 0:
                print("No lines given to generate. Resetting back to input.")
                continue
            start_gens(gen_lines,count)

# Does all generations in file. Expects each line in the file to be in form:
# Character speaker
# Text
# NEW/EMPTY LINE ("\n")
def read_lines(file,count = 1,lang = 'en',limit = 200):
    a = os.path.realpath(os.path.normpath(file))
    gen_lines = []
    with open(a,'rb') as file:
        for line in file:
            line = line.decode().strip().replace('\t','')
            if not (line.isalnum()):
                continue
            # Here, speaker is the first item in tuple, text is the second.
            # We consider speaker as the first character. The emotion is the very next.
            # H - Happy, S - Sad, A - Angry, E - Embarrassed, T - Thinking, C - Curious, P - Surprised
            raw_line = (line.strip(),file.readline().decode().strip())
            character = raw_line[0][0]
            text = raw_line[1]
            emotion = emotions["N"] if len(raw_line[0]) < 2 else raw_line[0][1]

            # If our text went over the limit of the split (250, but use lower to keep it sounding good), separate and add another unique line.
            if len(text) > limit:
                texts = get_limited_sentences(text,limit)
                print('\nText was above 200. Lists of texts to go through:',texts)
                for t in texts:
                    line = "" + character + ",|" + t +",|" + lang + ",|" + emotion
                    print('From the split, now doing text:',t)
                    gen_lines.append(sanitize(line))
                print()
            else:
                # OPTIONAL: for Snake
                #if raw_line[0] == "S":
                #    line += ",|1.5"
                line = "" + character + ",|" + text +",|" + lang + ",|" + emotion
                gen_lines.append(sanitize(line))
                
    # print("Lines to generate:",gen_lines)
    if len(gen_lines) <= 0:
        print("No lines to generate.")
        return {}
    else:
        return start_gens(gen_lines,count)
# TODO - Make script that takes in audio files
# Purpose: To automate listening to good takes and saving them sequentially to make dialogue
#   Lets you listen
#   Offers to save or discard or listen again
#   Names file with prefix
#   Numbers file for unique, if exists, next number
#   Add REDO to end of file if don't like the take.



# lines - List of generations to do with speaker, text, etc.
# count - How many generations to do per line
# show_speakers - Whether to print the speakers used in gen, defaults to False
# Returns a list of file names it generated
def start_gens(lines = [],count = 1, show_speakers = False,base_file = 'zO') -> dict[str,list[str]]:
    generated_dict: dict[str,list[str]] = {}
    gen_count = 0
    print("Total unique lines to generate: " + str(len(lines)) + ". Total lines * count: " + str(len(lines)*count))
    print("\nNow generating...\n")
    start = time.perf_counter()
    for i in range(len(lines)):
        for j in range(count):
            # For counting files
            current = i*count + j
            total = count*len(lines)
            
            # Naming for easier reading
            speaker_wav = lines[i][0]
            text = lines[i][1]
            lang = lines[i][2] or "en"
            emo = lines[i][3] or "Neutral"
            try:
                speed = float(lines[i][4] or 1.0)
            except ValueError:
                print(f'Could not convert speed (value: {speed}) to a float. Defaulting to 1.0')
                speed = 1.0
            split = lines[i][5] or False
            
            # Increment by 1 each iteration
            fn_speaker = os.path.basename(str(speaker_wav[0])).replace('.wav','')
            file = base_file + str(i).zfill(4) + "-" + str(j) + '-' + fn_speaker + '.wav'
            print('params:',lines[i])
            if not text or not lang or not speaker_wav:
                print(f"Couldn't parse iteration {i}, text: {text}, lang: {lang}, speaker_wav: {speaker_wav}")
                continue
            try:
                tts.tts_to_file(text=text, speaker_wav=speaker_wav,language=lang, file_path=file,emotion=emo,speed=speed,split_sentences=split)
            except Exception as e:
                print('Failed when trying to use tts generate. Data:',{'speaker_wav':speaker_wav,'language':lang,'file_path':file,'emotion':emo,'speed':speed,'split_sentences':split,'text':text})
                raise e
            if show_speakers:
                print("Using " + str(speaker_wav) + ", " + file + " complete. " + str(total - current - 1) + " remain.")
            else:
                print(file + " complete. " + str(total - current - 1) + " remain.")
            gen_count += 1
            # If we have a speaker already in the dict, add to its list the current file
            if generated_dict.get(fn_speaker):
                generated_dict[fn_speaker].append(os.path.join(os.getcwd(),file))
            # Otherwise, create the entry and store the first file associated with it
            else:
                generated_dict[fn_speaker] = [os.path.join(os.getcwd(),file)]
    time_taken = time.perf_counter() - start
    print("\nDone! Time taken: "+ str(time_taken) + " seconds, "+str(time_taken/float(60.0)) + " minutes.")
    print("Total generations: "+ str(gen_count) + '\n')
    return generated_dict

# For testing all combinations of wavs to get perfect voice
def testing(count = 1):
    lines = []
    text = input("\nEnter text to use for generations: ")
    sounds = input("Enter all sound wavs you want to use separated by ','. It will use all combinations of them: ")
    if len(sounds) <= 0 or len(text) <= 0:
        print("Cannot generate. Either text or sounds input was empty.")
    else:
        sounds = sounds.split(",")
        print()
        
        # Generate text with all combinations of wav files
        for i in range(len(sounds)):
            comb = itertools.combinations(sounds,i+1)
            for j in comb:
                line = ",".join(list(j)) + ",|" + text + ",|en,|,|"
                lines.append(sanitize(line))
        start_gens(lines,count,show_speakers=True)
        
def handle_file_mode(count = 1,skip = False):
    files = lang_limit = ''
    # For RVC with multi-file allow
    # Each entry is considered to be one file.
    gen_files: dict[str,list[str]] = {}
    if skip:
        files = 'text.txt'
    else:
        files = input('Enter list of files to read from separated by ",|" Leave blank to default to the test.txt: ')
        lang_limit = input('Enter 2 character language (en,ja,etc) and limit separatetd by , or leave blank for english and 200 char limit. Ex en,200: ')
    if len(files) == 0:
        files = ['test.txt']
    else:
        files = files.split(',')
    if len(lang_limit) < 2:
        lang = 'en'
        limit = 200
    else:
        lang,limit = lang_limit.split(',|')
    print('Files to go through:',files)
    for file in files:
        try:
            gen_files = read_lines(file,count,lang,limit)
            # Handle RVC. The idea is to run it for as many times as we have speakers, associating the speaker with a given index and model.
            handle_rvc(gen_files,skip=skip,input_path=os.path.dirname(file))
        except Exception as e:
            print('Error occured in file loop. File was:',file)
            raise
 
def handle_rvc(gen_files: dict[str,list[str]] = None,r_args:dict[str,str] = None,rvc_root = '',speaker_list: list[str] = None,skip = False,input_path = ''):
    # If we don't have any files given, it's presumed that we either set up dir/list in args already or will do so now.
    good = False
    rvc_args = r_args or get_default_rvc_args()
    if not skip:
        rvc_choice = input('Do you want to do RVC? y or anything else: ')
    else:
        rvc_choice = 'y'
    if rvc_choice == 'y':
        good = True
        # No point for the code below? As it's processed in run_rvc. Is this func needed?
        
        # print('Generated files:',gen_files)
        rvc_root = rvc_root or 'C:/Users/Kevin/Desktop/stuff/stable-diffusion/TTS/RVC1006Nvidia'
        # good = False
        # rvc_args = r_args or get_default_rvc_args()
        # input_path = input_path or rvc_args['--input_path']
        # if skip:
        #     good = True
        # else:
        #     while True:
        #         print('Current Args:',rvc_args)
        #         args = input('\nEnter args of rvc in the form "<key><SPACE><value>", separating each pair with ,| Note the keys should be cli options, like --f0up_key,3 - ')
        #         if args and ' ' in args:
        #             args = args.split(',|')
        #             for key,value in map(lambda x: x.split(' '),args):
        #                 rvc_args[key] = value
        #             print('\nnew args to send to rvc:',rvc_args)
        #         ok = input('Is this okay? anything for yes, n for no (repeat this), q for quit. Enter r to reset the arg list: ')
        #         if ok:
        #             if ok == 'r':
        #                 rvc_args = get_default_rvc_args()
        #                 continue
        #             elif ok == 'q':
        #                 good = False
        #                 break
        #             elif ok == 'n':
        #                 continue
                    # good = True
                    # break
    if good:    
        run_rvc(rvc_root,rvc_args,gen_files,input_path,speaker_list,skip)
        
def change_rvc_args(rvc_args):
    backup_rvc_args = rvc_args
    while True:
        print('Current Args:',rvc_args)
        args = input('\nEnter args of rvc in the form "<key><SPACE><value>", separating each pair with ,| Note the keys should be cli options, like --f0up_key 3,|--index_path test.index - ')
        if args and ' ' in args:
            args = args.split(',|')
            for key,value in map(lambda x: x.split(' '),args):
                rvc_args[key] = value
            print('\nnew args to send to rvc:',rvc_args)
        else:
            print('No changes made to rvc args. Current rvc:',rvc_args)
        ok = input('Is this okay? anything for yes and keep looping, d for done and break. Enter r to reset the arg list: ')
        if ok:
            if ok == 'r':
                rvc_args = backup_rvc_args
            elif ok == 'd':
                break
    return rvc_args
              
# Note that input_path takes prio over file_dict  
def run_rvc(rvc_root = '',rvc_args: dict = None,file_dict:dict[str,list[str]] = None,input_path = '',speaker_list:list[str] = None,skip = False):
    # Basically, data struct for files will be {speaker: file_list} for however many speakers there are
    # If we are given a file dict, iterate over list of files for each key
    # If we don't have a speaker_list and have an input path, iterate over them all with same rvc settings
    # If input path and speaker list, setup file dict and then iterate as before
    # TODO: Rewrite to allow for each list ran through RVC to have its own separate rvc_args, determined by the user? Done by asking, but way to do it programmatically?
    print('\nSpeaker List:',speaker_list)
    time_taken = 0.0
    print('\nrvc_root:',rvc_root,'input_path:',input_path)
    print('file_dict:',file_dict)
    if not rvc_root:
        print('No root found, root given:',rvc_root)
        return
    elif not file_dict and (not input_path and file_dict and len(file_dict) == 0):
        print('Neither file_dict nor input_path given, nothing to run.')
        return
    # For each list of files, run RVC using the speaker to determine the model path and index file to use.
    file_list_dict = file_dict or {}
    if len(rvc_args) == 0:
        rvc_args = get_default_rvc_args()
    # Begin getting files to do.
    if (not file_dict or len(file_dict) == 0) and input_path:
        dir_files = os.listdir(input_path)
        # If we want to filter by speaker, assumes it's at end of file with - preceding
        # For each speaker, dict[speaker] = list of items in dir_files if file speaker = speaker. rvc_args are also separate
        if speaker_list:
            for speaker in speaker_list:
                file_list_dict[speaker] = [os.path.normpath(os.path.realpath(os.path.join(input_path,file))) for file in dir_files if \
                    file[len(file) - file[-1::-1].find('-'):].replace('.wav','') == speaker]
                
        # If not filtering on spekers, just get list of files and put them in as 'items'
        else:
            file_list_dict = {'items':list(map(lambda x: os.path.normpath(os.path.realpath(os.path.join(input_path,x))),dir_files))}
    # TODO: Put all code above into its own func

    # After setting up file_list_dict no matter what, time to run RVC with each list
    for speaker,file_list in file_list_dict.items():
        rvc_args['--input_list'] = ''
        str_file_list = ' '.join(file_list)
        if len(str_file_list) <= 0:
            rvc_args.pop('--input_list')
            print('No files gotten. Speaker:',speaker)
        else:
            if not skip:
                print('Speaker:',speaker)
                model = input('Enter model name to use. Will assume same name for .pth and .index (do not type in extension). Type "s" to skip: ')
                if model != 's':
                    if model and model != '':
                        rvc_args['--model_name'] = model + '.pth'
                        rvc_args['--index_path'] = model + '.index'
                    else:
                        rvc_args['--model_name'] = speaker_dict[speaker] + '.pth'
                        rvc_args['--index_path'] = speaker_dict[speaker] + '.index'
                    rvc_args = change_rvc_args(rvc_args)
            else:
                rvc_args['--model_name'] = speaker_dict[speaker] + '.pth'
                rvc_args['--index_path'] = speaker_dict[speaker] + '.index'
            rvc_args['--input_list'] = str_file_list
            rvc_args.pop('--input_path','No --input_path')
            # f0up_key = input('Enter semitones to shift, defaults to 5: ')
            # if f0up_key:
                # rvc_args['--f0up_key'] = f0up_key
            # Separate by speaker?
            # rvc_args['--opt_path'] = os.path.join(rvc_args['--opt_path'],speaker)
            pass_rvc_args = ' '.join(map(lambda x: str(x) + ' ' + str(rvc_args.get(x)),rvc_args))
            if model != 's':
                # Run RVC
                start = time.perf_counter()
                python_path = os.path.normpath(os.path.realpath(os.path.join(rvc_root,'venv/Scripts/python.exe')))
                rvc_batch_file = os.path.normpath(os.path.realpath(os.path.join(rvc_root,'tools/infer_batch_rvc.py')))
                cmd = '%s %s %s' % (python_path,rvc_batch_file,pass_rvc_args)
                # print('\nNow running RVC from input path with cmd:',cmd,'\n')
                try:
                    subprocess.call(cmd,cwd=rvc_root)
                except FileNotFoundError as e:
                    print("Couldn't find a file. Check cmd.")
                    print(f'winerror: {e.winerror}, file: {e.filename}, errorno: {e.errno}, strerror{e.strerror}')
                    print('CMD used:',cmd)
                except Exception as e:
                    print('Something went wrong. Raising...')
                    raise e
                time_taken += time.perf_counter() - start
    print(f'\nDone generating! Time taken: {time_taken} seconds and {time_taken/60.0} minutes.')
        
# For RVC
# Param explanations:
# f0_up_key - How many semitones to transpose voice
# input_path - The dir of wavs to use
# index_path - The index file, full path
# f0_method - The pitch extraction algorithm, default rmvpe (and best to leave at that), others are harvest,pm
# opt_path - The output dir
# model_name - The model file, full path
# index_rate - The search feature ratio. Per doc, controls accent strength, too high has artifacting. 0.75 works
# device - Which device to use (gpus, cpu), leave to cuda:0 for nvidia with cuda enabled
# is_half - Halves the generation before generating, lower precision but much faster
# filter_radius: Doc, >= 3 applies median filtering to harvested pitch, value is radius and reduces breathiness. 3
# resample_sr - sample rate (in hz) to resample audio. If 0, doesn't. Leave at 0
# rms_mix_rate - Volume envelope scaling. 0 mimics original volume, higher makes consistently loud. 0.25
# protect - Per doc, protect voiceless consonants and breath sounds to prevent tearing. 0.5 disables. 0.33
# Simply enter a index and model name and change params as desired. Defaults will also be fine
def get_default_rvc_args():
    rvc_args = {
        '--f0up_key': '5',
        '--input_path': os.path.join(os.getcwd(),'input_wavs'),
        '--index_path': 'test.index',
        '--f0method': 'rmvpe',
        '--opt_path': os.path.join(os.getcwd(),'opt'),
        '--model_name': 'test.pth',
        '--index_rate': '0.55',
        '--device': 'cuda:0',
        '--is_half': 'False',
        '--filter_radius': '3',
        '--resample_sr': '0',
        '--rms_mix_rate': '1.0',
        '--protect': '0.33',
        '--input_list': ''
    }
    return rvc_args

def main():
    rvc_root = os.path.normpath(os.path.realpath('path_to_RVC_root_dir'))
    while True:
        try:
            skip = input('\nSkip RVC questions and just run? y for yes, nothing for no: ')
            count = input("\nChoose how many gens to make per line. Type q to exit: ")
            if count == 'q' or count == 'Q':
                break
            if not count:
                continue
            count = int(count)
        except ValueError:
            print("Error: input received (" + str(count) + ") is not an integer.")
            continue
        choice = input("Choose mode. 1 for being able to type lines with speaker and text, 2 for reading file. 3 for testing all combinations of wavs. 4 for transforming all files in dir to RVC using dict for speakers. Type q to quit: ")
        if choice == "1":
            custom(count)
        elif choice == "2":
            handle_file_mode(count,skip)
        elif choice == "3":
            testing(count)
        elif choice == '4':
            input_path = input('Enter directory where the raw wavs are that will be run through RVC. Leave blank for cwd/input_wavs: ')
            rvc_args = get_default_rvc_args()
            speakers = speaker_dict
            if not input_path or input_path == '':
                input_path = os.path.join(os.getcwd(),'input_wavs')
                print('No input path given. Defaulting to:',input_path)
            handle_rvc(r_args=rvc_args,rvc_root = rvc_root,speaker_list=speakers,skip=skip,input_path=input_path)
        elif choice == 'q' or choice == 'Q':
            break
        else:
            continue

if __name__ == '__main__':
    main()