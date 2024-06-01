import os
import spacy
from lxml import etree
from spacy.matcher import DependencyMatcher
import csv
import pandas as pd

VAPs_dict = {"croire" : 5.03, "savoir" : 8.65, "penser" : 5.46, "juger" : 7.40, "reconnaître" : 6.85, "trouver" : 5.85, "supposer" : 3.29, "apercevoir" : 'nan', "éprouver" : 8, "voir" : 5, "connaître" : 7, "concevoir" : 6, "conjecturer" : 5 , "remarquer" : 7 , 'douter' : 'nan', 'affirmer' : 'nan', 'nier':'nan'}
ADVs_negation = ['pas', 'ne', 'aucunement']

def parser_xml(fichier_xml):
    namespaces = {'tei': 'http://www.tei-c.org/ns/1.0', 'xml': 'http://www.w3.org/XML/1998/namespace'}
    # Parse the XML file
    tree = etree.parse(fichier_xml)
    root = tree.getroot()
    # Lists to store divs and phrases for the current file
    divs = []
    phrases = []
    # Extract div elements
    div_elements = root.xpath('.//tei:div[@xml:id]', namespaces=namespaces)
    for div in div_elements:
        div_id = div.get('{http://www.w3.org/XML/1998/namespace}id')
        # Extract s elements under this div
        s_elements = div.xpath('.//tei:s', namespaces=namespaces)
        # Extract sentences from s elements
        for s in s_elements:
            divs.append(div_id)
            phrases.append(str(s.xpath("string()")))
        # Create the DataFrame for the current file
        df_generale = pd.DataFrame({'Divs': divs, 'Phrases': phrases})
    return df_generale

def nlp_pipeline(phrases, nlp):
    docs = list(nlp.pipe(phrases))
    return docs

def chercher_VAPS(doc_objects, df, pattern, matcher):
    divs_list = []
    source_list = []
    vap_list = []
    vap_values = []
    adv_list = []
    lemmas = []
    target_list = []
    target_lemma = []
    phrases_list = []
    index = 0
    for doc in doc_objects:
        verbs_with_mood_sub = [token for token in doc if token.pos_ == "VERB" and "Mood=Sub" in token.morph]
        matches = matcher(doc)
        filtered_matches = [(match_id, token_ids) for match_id, token_ids in matches
                                    if not any(doc[token_id].pos_ == "VERB" and doc[token_id] in verbs_with_mood_sub
                                               for token_id in token_ids)]
        for match_id, token_ids in filtered_matches:
            vap = token_ids[0]
            subject = token_ids[1]
            obj = token_ids[2]
            source_list.append(doc[subject])
            vap_list.append(doc[vap])
            vap_values.append(VAPs_dict.get(doc[vap].lemma_))
            lemmas.append(doc[vap].lemma_)
            target_list.append(" ".join([t.text for t in doc[obj].subtree]))
            target_lemma.append(" ".join([t.lemma_ for t in doc[obj].subtree]))
            phrases_list.append(doc[vap].sent)
            adv_list.append("NAN")
            divs_list.append(df['Divs'][index])
        index += 1
    df_dict = {'Divs': divs_list, 'Source' : source_list, 'VAP' : vap_list, 'Lemma' : lemmas, 'VAP_values': vap_values, "ADV" : adv_list, "Target" : target_list, "Target_lemma" : target_lemma, 'Phrase Complete' : phrases_list}
    df_PAPs = pd.DataFrame(df_dict)
    return df_PAPs

def chercher_ADVs(df, pattern, matcher):
    dict_index_value = {}
    for index, row in df.iterrows():
        doc = row['Phrase Complete']
        matches = matcher(doc)
        for m_id, t_id in matches:
            adv = t_id[2]
            #print(index, doc[adv])
            dict_index_value[index] = doc[adv].text
    for index, value in dict_index_value.items():
        df.at[index, 'ADV'] = value
    mask = df['ADV'].isin(ADVs_negation)
    df = df[~mask]
    return df

def chercher_COND(df, pattern, matcher):
    dict_index_value2 = {}
    list_index_COND = []
    for index, row in df.iterrows():
        doc = row['Phrase Complete']
        vap = row['VAP']
        matches = matcher(doc)
        for m_id, t_id in matches:
            mark = t_id[2]
            VAP = t_id[0]
            if vap == doc[VAP]:
                list_index_COND.append(index)
    df2 = df.drop(list_index_COND, errors='ignore')
    return df2

def drop_not_that_clauses(df):
    df = df[df['Target'].str.startswith('qu')]
    return df

# def df_to_csv(df):
#     df_THAT_clause.to_csv('meditations.csv', index=False)