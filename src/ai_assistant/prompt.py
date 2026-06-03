from __future__ import annotations

import os

from lightrag.prompt import PROMPTS

PROMPTS_LANGUAGE = os.getenv("PROMPTS_LANGUAGE", "Italian")

PROMPTS["DEFAULT_DATATYPES"] = ["number", "datetime", "string", "boolean"]

if PROMPTS_LANGUAGE == "Italian":

    PROMPTS["entity_extraction"] = """---Ruolo---
Sei un esperto di analisi semantica in grado di individuare i tipi di entità e le relazioni presenti in un testo.

---Obiettivo---
Ricevuto un testo, restituire tutti i tipi di entità presenti nel testo, ciascuno con le proprie caratteristiche, e tutte le relazioni che legano tra di loro i tipi di entità restituiti.

---Regole di restituzione di entità e relazioni---
- Assegnare a tipi di entità, caratteristiche e relazioni, nomi al singolare e sempre diversi tra di loro.
- Comporre i nomi dei tipi di entità, delle caratteristiche e delle relazioni in modalità {iri_format} senza spazi.
- Restituire i nomi dei tipi di entità, delle caratteristiche e delle relazioni in **{iri_language}**.
- Restituire le descrizioni dei tipi di entità, delle caratteristiche e delle relazioni in **{language}**.

---Fasi---
Fase 1. Trovare tutti i tipi di entità. Per ogni tipo di entità restituisci le seguenti informazioni:
- entity_type_name: il nome in **{iri_language}** del tipo di entità. Metti l'iniziale del nome in maiuscolo.
- entity_type_description: una descrizione comprensibile in **{language}** dei compiti e delle attività del tipo di entità.
Componi ciascun tipo di entità così: ("entity_type"{tuple_delimiter}<entity_type_name>{tuple_delimiter}<entity_type_description>){record_delimiter}

Fase 2. A partire dai tipi di entità trovati nella Fase 1, individuare tutte le caratteristiche che sono *evidenti dimensioni o proprietà* delle entità di quel tipo.
Per ogni caratteristica restituisci le seguenti informazioni:
- characteristic_name: il nome in **{iri_language}** della caratteristica.
- characteristic_entity_type: il nome del tipo di entità, trovato nella Fase 1, a cui la caratteristica si riferisce
- characteristic_datatype: il tipo di valore assunto dalla caratteristica, selezionato tra i seguenti tipi: {datatypes}
- characteristic_description: una descrizione comprensibile in **{language}** della caratteristica trovata
Componi ciascuna caratteristica così: ("characteristic"{tuple_delimiter}<characteristic_name>{tuple_delimiter}<characteristic_entity_type>{tuple_delimiter}<characteristic_datatype>{tuple_delimiter}<characteristic_description>){record_delimiter}

Fase 3. A partire dai tipi di entità trovati nella Fase 1, individuare tutte le coppie (sub_entity_type, super_entity_type) in cui il secondo tipo di entità è una *evidente generalizzazione* del primo.
Per ogni coppia di tipi di entità restituisci le seguenti informazioni:
- sub_entity_type: il nome del tipo di entità particolare, così come identificato nella Fase 1
- super_entity_type: il nome del tipo di entità generale, così come identificato nella Fase 1
Componi ciascuna generalizzazione così: ("subclass"{tuple_delimiter}<sub_entity_type>{tuple_delimiter}<super_entity_type>){record_delimiter}

Fase 4. A partire dai tipi di entità trovati nella Fase 1, individuare tutte le coppie (source_entity_type, target_entity_type) che sono *evidentemente legati* uno con l'altro.
Per ogni coppia di tipi di entità restituisci le seguenti informazioni:
- relationship_name: il nome in **{iri_language}** della relazione.
- source_entity_type: il nome del tipo di entità di partenza, così come identificato nella Fase 1
- target_entity_type: il nome del tipo di entità di arrivo, così come identificato nella Fase 1
- relationship_description: una spiegazione in **{language}** del motivo per cui ritieni che il tipo di entità di partenza e il tipo di entità di arrivo sono legati l'uno all'altro
- relationship_strength: un valore numerico che indica l'intensità del legame tra il tipo di entità di partenza e il tipo di entità di arrivo
Componi ciascuna relazione così: ("relationship"{tuple_delimiter}<relationship_name>{tuple_delimiter}<source_entity_type>{tuple_delimiter}<target_entity_type>{tuple_delimiter}<relationship_description>{tuple_delimiter}<relationship_strength>){record_delimiter}

Fase 5. Restituisci il risultato come una lista dei tipi di entità, caratteristiche e relazioni trovate nella Fasi 1, 2 and 3. Usa **{record_delimiter}** come separatore degli elementi della lista.

Fase 6. Al termine, scrivi {completion_delimiter}

#############################
---Real Data---
######################
Testo:
{input_text}
######################
Risultato:
"""

    PROMPTS["entity_extraction_SC_examples"] = [
        """Esempio 1:

Testo:
```Un luogo di lavoro è uno spazio fisico dedicato alle attività operative di un’organizzazione e quindi ospita i suoi dipendenti affinché possano svolgere i propri compiti utilizzando gli eventuali strumenti messi a loro disposizione nel luogo stesso.
Il luogo di lavoro è anche un luogo pubblico poiché quest’ultimo per consentire di erogare i servizi al pubblico deve necessariamente prevedere la presenza di personale addetto a tale erogazione.
Il luogo di lavoro è caratterizzato da un numero massimo di addetti che possono essere contemporaneamente presenti nei suoi orari di funzionamento.
```
######################
Risultato:
("entity_type"{tuple_delimiter}"Luogo_di_lavoro"{tuple_delimiter}"Un luogo di lavoro è uno spazio fisico dove si svolgono le attività operative di una organizzazione."){record_delimiter}
("entity_type"{tuple_delimiter}"Organizzazione"{tuple_delimiter}"Una organizzazione è un gruppo di persone che operano in modo coordinato per raggiungere un obiettivo comune."){record_delimiter}
("entity_type"{tuple_delimiter}"Dipendente"{tuple_delimiter}"Una persona fisica che viene retribuito per lavorare sotto la direzione operativa di qualcun altro."){record_delimiter}
("entity_type"{tuple_delimiter}"Postazione_di_lavoro"{tuple_delimiter}"Un'area di spazio dove si può svolgere un determinato lavoro."){record_delimiter}
("entity_type"{tuple_delimiter}"Luogo_pubblico"{tuple_delimiter}"Un particolare luogo dove le persone possono ottenere alcuni servizi desiderati."){record_delimiter}
("characteristic"{tuple_delimiter}"numero_massimo_dipendenti"{tuple_delimiter}"Luogo_di_lavoro"{tuple_delimiter}"number"{tuple_delimiter}"Massimo numero di dipendenti che possono operare contemporaneamente in uno stesso luogo di lavoro."){record_delimiter}
("characteristic"{tuple_delimiter}"orario_di_apertura"{tuple_delimiter}"Luogo_di_lavoro"{tuple_delimiter}"string"{tuple_delimiter}"Orario di apertura al pubblico di un luogo di lavoro."){record_delimiter}
("subclass"{tuple_delimiter}"Luogo_di_lavoro"{tuple_delimiter}"Luogo_pubblico"{tuple_delimiter}){record_delimiter}
("relationship"{tuple_delimiter}"ha_luogo_di_lavoro"{tuple_delimiter}"Organizzazione"{tuple_delimiter}"Luogo_di_lavoro "{tuple_delimiter}"Associa una organizzazione al suo luogo di lavoro."{tuple_delimiter}8){record_delimiter}
("relationship"{tuple_delimiter}"ha_organizzazione"{tuple_delimiter}"Dipendente"{tuple_delimiter}"Organizzazione"{tuple_delimiter}"Lega un dipendente all'organizzazione per cui lavora."{tuple_delimiter}8){record_delimiter}
("relationship"{tuple_delimiter}"ha_postazione_di_lavoro"{tuple_delimiter}"Dipendente"{tuple_delimiter}"Postazione_di_lavoro"{tuple_delimiter}"Lega un dipendente alla postazione di lavoro in cui opera."{tuple_delimiter}7){record_delimiter}
{completion_delimiter}
#############################""",
        """Esempio 2:

Testo:
```Un conferimento è un ruolo assunto da una persona e attiene a una assegnazione disposta da un ente pubblico mediante uno specifico atto di conferimento.
La selezione della persona idonea ad assumere un conferimento avviene con una procedura concorsuale.
Il conferimento è definito mediante: un nome, una descrizione che ne definisce l'obiettivo operativo, una data di inizio e fine e una retribuzione.
```
######################
Risultato:
("entity_type"{tuple_delimiter}"Conferimento"{tuple_delimiter}"Un conferimento è un ruolo assunto da una persona relativamente ad una assegnazione stabilita da un ente pubblico."){record_delimiter}
("entity_type"{tuple_delimiter}"Persona_fisica"{tuple_delimiter}"Il soggetto che può ricevere un conferimento."){record_delimiter}
("entity_type"{tuple_delimiter}"Ente_pubblico"{tuple_delimiter}"Il soggetto che può assegnare un conferimento."){record_delimiter}
("entity_type"{tuple_delimiter}"Atto_di_conferimento"{tuple_delimiter}"Lo strumento legale con cui viene assegnato un conferimento."){record_delimiter}
("entity_type"{tuple_delimiter}"Procedura_concorsuale"{tuple_delimiter}"Il percorso di selezione mediante il quale viene scelta la persona più idonea per ricevere l'incarico da conferire'."){record_delimiter}
("characteristic"{tuple_delimiter}"nome"{tuple_delimiter}"Conferimento"{tuple_delimiter}"string"{tuple_delimiter}"Il nome del conferimento."){record_delimiter}
("characteristic"{tuple_delimiter}"descrizione"{tuple_delimiter}"Conferimento"{tuple_delimiter}"string"{tuple_delimiter}"La descrizione dell'obiettivo operativo assegnato con il conferimento."){record_delimiter}
("characteristic"{tuple_delimiter}"data_inizio"{tuple_delimiter}"Conferimento"{tuple_delimiter}"datetime"{tuple_delimiter}"La data di avvio del conferimento."){record_delimiter}
("characteristic"{tuple_delimiter}"data_fine"{tuple_delimiter}"Conferimento"{tuple_delimiter}"datetime"{tuple_delimiter}"La data di termine del conferimento."){record_delimiter}
("characteristic"{tuple_delimiter}"retribuzione"{tuple_delimiter}"Conferimento"{tuple_delimiter}"number"{tuple_delimiter}"Il compenso attribuito al conferimento."){record_delimiter}
("relationship"{tuple_delimiter}"ha_conferimento"{tuple_delimiter}"Persona_fisica"{tuple_delimiter}"Conferimento"{tuple_delimiter}"Associa una persona al conferimento assegnatogli."{tuple_delimiter}8){record_delimiter}
("relationship"{tuple_delimiter}"conferimento_assegnato_da"{tuple_delimiter}"Conferimento"{tuple_delimiter}"Ente_pubblico"{tuple_delimiter}"Associa un conferimento con l'ente che lo ha assegnato."{tuple_delimiter}8){record_delimiter}
("relationship"{tuple_delimiter}"conferimento_assegnato_con"{tuple_delimiter}"Conferimento"{tuple_delimiter}"Atto_di_conferimento"{tuple_delimiter}"Associa un conferimento con l'atto legale che lo ha assegnato."{tuple_delimiter}6){record_delimiter}
("relationship"{tuple_delimiter}"ente_pubblico_emette_atto"{tuple_delimiter}"Ente_pubblico"{tuple_delimiter}"Atto_di_conferimento"{tuple_delimiter}"Lega un ente pubblico che ha emesso un atto di conferimento con l'atto stesso."{tuple_delimiter}6){record_delimiter}
("relationship"{tuple_delimiter}"ha_candidato_vincitore"{tuple_delimiter}"Procedura_concorsuale"{tuple_delimiter}"Persona_fisica"{tuple_delimiter}"Lega una procedura concorsuale con la persona che si è aggiudicato il concorso stesso."{tuple_delimiter}7){record_delimiter}
{completion_delimiter}
#############################""",
        """Esempio 3:

Testo:
```Una filiera alimentare è caratterizzata dal prodotto alimentare a cui da origine, con ciò intendendo, secondo la normativa europea, 'una qualsiasi sostanza o prodotto trasformato, parzialmente trasformato o non trasformato, destinato ad essere ingerito, o di cui si prevede ragionevolmente che possa essere ingerito, da esseri umani'.
Considerando i prodotti alimentari disponibili sul mercato, essi sono classificati in base alla categoria merceologica a cui appartengono. Queste categorie sono ordinate gerarchicamente e raggruppano tutti i prodotti che possono essere commercializzati quindi non solo prodotti alimentari ma anche prodotti che non sono destinati al consumo alimentare umano così come le cosiddette "eccedenze" cioè prodotti alimentari che hanno perso l’idoneità alla loro destinazione d’uso ma che risultano ancora utilizzabili per il consumo alimentare umano, prima di divenire rifiuti, anch'essi classificati da opportune categorie.
In generale queste sono tutte tipologie di prodotto ovvero quantità di aliquote di materia.
```
######################
Risultato:
("entity_type"{tuple_delimiter}"Prodotto"{tuple_delimiter}"Aliquota di materia."){record_delimiter}
("entity_type"{tuple_delimiter}"Prodotto_alimentare"{tuple_delimiter}"Prodotto trasformato, parzialmente trasformato o non trasformato, destinato ad essere ingerito, o di cui si prevede ragionevolmente che possa essere ingerito, da esseri umani."){record_delimiter}
("entity_type"{tuple_delimiter}"Prodotto_non_alimentare"{tuple_delimiter}"Prodotto non destinato al consumo alimentare umano."){record_delimiter}
("entity_type"{tuple_delimiter}"Eccedenza"{tuple_delimiter}"Prodotto alimentare che ha perso l’idoneità alla sua destinazione d’uso ma che risulta ancora utilizzabile per il consumo alimentare umano."){record_delimiter}
("entity_type"{tuple_delimiter}"Rifiuto"{tuple_delimiter}"Prodotto destinato allo smaltimento poiché non più commestibile."){record_delimiter}
("entity_type"{tuple_delimiter}"Categoria"{tuple_delimiter}"Ambito di pertinenza di un oggetto o prodotto."){record_delimiter}
("entity_type"{tuple_delimiter}"Categoria_merceologica"{tuple_delimiter}"Categoria di prodotti che possono essere commercializzati."){record_delimiter}
("entity_type"{tuple_delimiter}"Categoria_di_rifiuto"{tuple_delimiter}"Categoria di prodotti destinati allo smaltimento come rifiuto."){record_delimiter}
("characteristic"{tuple_delimiter}"quantità"{tuple_delimiter}"Prodotto"{tuple_delimiter}"number"{tuple_delimiter}"Quantità di aliquota di materia presente in un prodotto."){record_delimiter}
("characteristic"{tuple_delimiter}"nome_prodotto"{tuple_delimiter}"Prodotto"{tuple_delimiter}"string"{tuple_delimiter}"Nome identificativo di un prodotto."){record_delimiter}
("characteristic"{tuple_delimiter}"nome_categoria"{tuple_delimiter}"Categoria"{tuple_delimiter}"string"{tuple_delimiter}"Nome identificativo di una categoria."){record_delimiter}
("subclass"{tuple_delimiter}"Prodotto_alimentare"{tuple_delimiter}"Prodotto"){record_delimiter}
("subclass"{tuple_delimiter}"Prodotto_non_alimentare"{tuple_delimiter}"Prodotto"){record_delimiter}
("subclass"{tuple_delimiter}"Eccedenza"{tuple_delimiter}"Prodotto"){record_delimiter}
("subclass"{tuple_delimiter}"Rifiuto"{tuple_delimiter}"Prodotto"){record_delimiter}
("subclass"{tuple_delimiter}"Categoria_merceologica"{tuple_delimiter}"Categoria"){record_delimiter}
("subclass"{tuple_delimiter}"Categoria_di_rifiuto"{tuple_delimiter}"Categoria"){record_delimiter}
("relationship"{tuple_delimiter}"ha_categoria"{tuple_delimiter}"Prodotto"{tuple_delimiter}"Categoria"{tuple_delimiter}"Legame tra un prodotto e la sua categoria."{tuple_delimiter}8){record_delimiter}
("relationship"{tuple_delimiter}"ha_sottocategoria"{tuple_delimiter}"Categoria"{tuple_delimiter}"Categoria"{tuple_delimiter}"Rapporto gerarchico tra categorie."{tuple_delimiter}5){record_delimiter}
{completion_delimiter}
#############################""",
    ]

    PROMPTS["entity_extraction_CC_examples"] = [
        """Esempio 1:

Testo:
```Un luogo di lavoro è uno spazio fisico dedicato alle attività operative di un’organizzazione e quindi ospita i suoi dipendenti affinché possano svolgere i propri compiti utilizzando gli eventuali strumenti messi a loro disposizione nel luogo stesso.
Il luogo di lavoro è anche un luogo pubblico poiché quest’ultimo per consentire di erogare i servizi al pubblico deve necessariamente prevedere la presenza di personale addetto a tale erogazione.
Il luogo di lavoro è caratterizzato da un numero massimo di addetti che possono essere contemporaneamente presenti nei suoi orari di funzionamento.
```
######################
Risultato:
("entity_type"{tuple_delimiter}"LuogoDiLavoro"{tuple_delimiter}"Un luogo di lavoro è uno spazio fisico dove si svolgono le attività operative di una organizzazione."){record_delimiter}
("entity_type"{tuple_delimiter}"Organizzazione"{tuple_delimiter}"Una organizzazione è un gruppo di persone che operano in modo coordinato per raggiungere un obiettivo comune."){record_delimiter}
("entity_type"{tuple_delimiter}"Dipendente"{tuple_delimiter}"Una persona fisica che viene retribuito per lavorare sotto la direzione operativa di qualcun altro."){record_delimiter}
("entity_type"{tuple_delimiter}"PostazioneDiLavoro"{tuple_delimiter}"Un'area di spazio dove si può svolgere un determinato lavoro."){record_delimiter}
("entity_type"{tuple_delimiter}"LuogoPubblico"{tuple_delimiter}"Un particolare luogo dove le persone possono ottenere alcuni servizi desiderati."){record_delimiter}
("characteristic"{tuple_delimiter}"numeroMassimoDipendenti"{tuple_delimiter}"LuogoDiLavoro"{tuple_delimiter}"number"{tuple_delimiter}"Massimo numero di dipendenti che possono operare contemporaneamente in uno stesso luogo di lavoro."){record_delimiter}
("characteristic"{tuple_delimiter}"orarioDiApertura"{tuple_delimiter}"LuogoDiLavoro"{tuple_delimiter}"string"{tuple_delimiter}"Orario di apertura al pubblico di un luogo di lavoro."){record_delimiter}
("subclass"{tuple_delimiter}"LuogoDiLavoro"{tuple_delimiter}"LuogoPubblico"{tuple_delimiter}){record_delimiter}
("relationship"{tuple_delimiter}"haLuogoDiLavoro"{tuple_delimiter}"Organizzazione"{tuple_delimiter}"LuogoDiLavoro "{tuple_delimiter}"Associa una organizzazione al suo luogo di lavoro."{tuple_delimiter}8){record_delimiter}
("relationship"{tuple_delimiter}"haOrganizzazione"{tuple_delimiter}"Dipendente"{tuple_delimiter}"Organizzazione"{tuple_delimiter}"Lega un dipendente all'organizzazione per cui lavora."{tuple_delimiter}8){record_delimiter}
("relationship"{tuple_delimiter}"haPostazioneDiLavoro"{tuple_delimiter}"Dipendente"{tuple_delimiter}"PostazioneDiLavoro"{tuple_delimiter}"Lega un dipendente alla postazione di lavoro in cui opera."{tuple_delimiter}7){record_delimiter}
{completion_delimiter}
#############################""",
        """Esempio 2:

Testo:
```Un conferimento è un ruolo assunto da una persona e attiene a una assegnazione disposta da un ente pubblico mediante uno specifico atto di conferimento.
La selezione della persona idonea ad assumere un conferimento avviene con una procedura concorsuale.
Il conferimento è definito mediante: un nome, una descrizione che ne definisce l'obiettivo operativo, una data di inizio e fine e una retribuzione.
```
######################
Risultato:
("entity_type"{tuple_delimiter}"Conferimento"{tuple_delimiter}"Un conferimento è un ruolo assunto da una persona relativamente ad una assegnazione stabilita da un ente pubblico."){record_delimiter}
("entity_type"{tuple_delimiter}"PersonaFisica"{tuple_delimiter}"Il soggetto che può ricevere un conferimento."){record_delimiter}
("entity_type"{tuple_delimiter}"EntePubblico"{tuple_delimiter}"Il soggetto che può assegnare un conferimento."){record_delimiter}
("entity_type"{tuple_delimiter}"AttoDiConferimento"{tuple_delimiter}"Lo strumento legale con cui viene assegnato un conferimento."){record_delimiter}
("entity_type"{tuple_delimiter}"ProceduraConcorsuale"{tuple_delimiter}"Il percorso di selezione mediante il quale viene scelta la persona più idonea per ricevere l'incarico da conferire'."){record_delimiter}
("characteristic"{tuple_delimiter}"nome"{tuple_delimiter}"Conferimento"{tuple_delimiter}"string"{tuple_delimiter}"Il nome del conferimento."){record_delimiter}
("characteristic"{tuple_delimiter}"descrizione"{tuple_delimiter}"Conferimento"{tuple_delimiter}"string"{tuple_delimiter}"La descrizione dell'obiettivo operativo assegnato con il conferimento."){record_delimiter}
("characteristic"{tuple_delimiter}"dataInizio"{tuple_delimiter}"Conferimento"{tuple_delimiter}"datetime"{tuple_delimiter}"La data di avvio del conferimento."){record_delimiter}
("characteristic"{tuple_delimiter}"dataFine"{tuple_delimiter}"Conferimento"{tuple_delimiter}"datetime"{tuple_delimiter}"La data di termine del conferimento."){record_delimiter}
("characteristic"{tuple_delimiter}"retribuzione"{tuple_delimiter}"Conferimento"{tuple_delimiter}"number"{tuple_delimiter}"Il compenso attribuito al conferimento."){record_delimiter}
("relationship"{tuple_delimiter}"haConferimento"{tuple_delimiter}"PersonaFisica"{tuple_delimiter}"Conferimento"{tuple_delimiter}"Associa una persona al conferimento assegnatogli."{tuple_delimiter}8){record_delimiter}
("relationship"{tuple_delimiter}"conferimentoAssegnatoDa"{tuple_delimiter}"Conferimento"{tuple_delimiter}"EntePubblico"{tuple_delimiter}"Associa un conferimento con l'ente che lo ha assegnato."{tuple_delimiter}8){record_delimiter}
("relationship"{tuple_delimiter}"conferimentoAssegnatoCon"{tuple_delimiter}"Conferimento"{tuple_delimiter}"AttoDiConferimento"{tuple_delimiter}"Associa un conferimento con l'atto legale che lo ha assegnato."{tuple_delimiter}6){record_delimiter}
("relationship"{tuple_delimiter}"entePubblicoEmetteAtto"{tuple_delimiter}"EntePubblico"{tuple_delimiter}"AttoDiConferimento"{tuple_delimiter}"Lega un ente pubblico che ha emesso un atto di conferimento con l'atto stesso."{tuple_delimiter}6){record_delimiter}
("relationship"{tuple_delimiter}"haCandidatoVincitore"{tuple_delimiter}"ProceduraConcorsuale"{tuple_delimiter}"PersonaFisica"{tuple_delimiter}"Lega una procedura concorsuale con la persona che si è aggiudicato il concorso stesso."{tuple_delimiter}7){record_delimiter}
{completion_delimiter}
#############################""",
        """Esempio 3:

Testo:
```Una filiera alimentare è caratterizzata dal prodotto alimentare a cui da origine, con ciò intendendo, secondo la normativa europea, 'una qualsiasi sostanza o prodotto trasformato, parzialmente trasformato o non trasformato, destinato ad essere ingerito, o di cui si prevede ragionevolmente che possa essere ingerito, da esseri umani'.
Considerando i prodotti alimentari disponibili sul mercato, essi sono classificati in base alla categoria merceologica a cui appartengono. Queste categorie sono ordinate gerarchicamente e raggruppano tutti i prodotti che possono essere commercializzati quindi non solo prodotti alimentari ma anche prodotti che non sono destinati al consumo alimentare umano così come le cosiddette "eccedenze" cioè prodotti alimentari che hanno perso l’idoneità alla loro destinazione d’uso ma che risultano ancora utilizzabili per il consumo alimentare umano, prima di divenire rifiuti, anch'essi classificati da opportune categorie.
In generale queste sono tutte tipologie di prodotto ovvero quantità di aliquote di materia.
```
######################
Risultato:
("entity_type"{tuple_delimiter}"Prodotto"{tuple_delimiter}"Aliquota di materia."){record_delimiter}
("entity_type"{tuple_delimiter}"ProdottoAlimentare"{tuple_delimiter}"Prodotto trasformato, parzialmente trasformato o non trasformato, destinato ad essere ingerito, o di cui si prevede ragionevolmente che possa essere ingerito, da esseri umani."){record_delimiter}
("entity_type"{tuple_delimiter}"ProdottoNonAlimentare"{tuple_delimiter}"Prodotto non destinato al consumo alimentare umano."){record_delimiter}
("entity_type"{tuple_delimiter}"Eccedenza"{tuple_delimiter}"Prodotto alimentare che ha perso l’idoneità alla sua destinazione d’uso ma che risulta ancora utilizzabile per il consumo alimentare umano."){record_delimiter}
("entity_type"{tuple_delimiter}"Rifiuto"{tuple_delimiter}"Prodotto destinato allo smaltimento poiché non più commestibile."){record_delimiter}
("entity_type"{tuple_delimiter}"Categoria"{tuple_delimiter}"Ambito di pertinenza di un oggetto o prodotto."){record_delimiter}
("entity_type"{tuple_delimiter}"CategoriaMerceologica"{tuple_delimiter}"Categoria di prodotti che possono essere commercializzati."){record_delimiter}
("entity_type"{tuple_delimiter}"CategoriaDiRifiuto"{tuple_delimiter}"Categoria di prodotti destinati allo smaltimento come rifiuto."){record_delimiter}
("characteristic"{tuple_delimiter}"quantità"{tuple_delimiter}"Prodotto"{tuple_delimiter}"number"{tuple_delimiter}"Quantità di aliquota di materia presente in un prodotto."){record_delimiter}
("characteristic"{tuple_delimiter}"nomeProdotto"{tuple_delimiter}"Prodotto"{tuple_delimiter}"string"{tuple_delimiter}"Nome identificativo di un prodotto."){record_delimiter}
("characteristic"{tuple_delimiter}"nomeCategoria"{tuple_delimiter}"Categoria"{tuple_delimiter}"string"{tuple_delimiter}"Nome identificativo di una categoria."){record_delimiter}
("subclass"{tuple_delimiter}"ProdottoAlimentare"{tuple_delimiter}"Prodotto"){record_delimiter}
("subclass"{tuple_delimiter}"ProdottoNonAlimentare"{tuple_delimiter}"Prodotto"){record_delimiter}
("subclass"{tuple_delimiter}"Eccedenza"{tuple_delimiter}"Prodotto"){record_delimiter}
("subclass"{tuple_delimiter}"Rifiuto"{tuple_delimiter}"Prodotto"){record_delimiter}
("subclass"{tuple_delimiter}"CategoriaMerceologica"{tuple_delimiter}"Categoria"){record_delimiter}
("subclass"{tuple_delimiter}"CategoriaDiRifiuto"{tuple_delimiter}"Categoria"){record_delimiter}
("relationship"{tuple_delimiter}"haCategoria"{tuple_delimiter}"Prodotto"{tuple_delimiter}"Categoria"{tuple_delimiter}"Legame tra un prodotto e la sua categoria."{tuple_delimiter}8){record_delimiter}
("relationship"{tuple_delimiter}"haSottocategoria"{tuple_delimiter}"Categoria"{tuple_delimiter}"Categoria"{tuple_delimiter}"Rapporto gerarchico tra categorie."{tuple_delimiter}5){record_delimiter}
{completion_delimiter}
#############################""",
    ]

    # Ricevi in ingresso uno o due nomi di oggetti e un elenco di descrizioni tutte riferite allo stesso oggetto o coppia di oggetti.

    PROMPTS[
        "summarize_entity_descriptions"
    ] = """Sei un assistente in grado di produrre un esauriente riassunto dei dati in ingresso.
Ricevi in ingresso uno o più nomi di oggetti e un elenco di descrizioni tutte riferite allo stesso oggetto o insieme di oggetti.
Cortesemente, riassumi tutto ciò in una unica comprensibile descrizione. Abbi cura di includere tutte le informazioni presenti nelle descrizioni ricevute.
Se le descrizioni di partenza sono in conflitto, risolvi i conflitti producendo un unico e chiaro riassunto.
Cita nella descrizione risultato i nomi degli oggetti.
Restituisci soltanto il riassunto senza aggiungere alcuna premessa o commento.
Usa {language} come lingua del risultato.

#######
---Data---
Nomi degli oggetti: {entity_name}
Elenco delle descrizioni: {description_list}
#######
Risultato:
"""

    PROMPTS[
        "entity_continue_extraction"
    ] = """Nell'ultima estrazione MOLTI tipi di entità e relazioni NON sono state restituite.

---Ricorda le fasi previste---

Fase 1. Trovare tutti i tipi di entità. Per ogni tipo di entità restituisci le seguenti informazioni:
- entity_type_name: il Nome del tipo di entità, in {iri_language}.
- entity_type_description: una descrizione comprensibile dei compiti e delle attività del tipo di entità
Componi ciascun tipo di entità così: ("entity_type"{tuple_delimiter}<entity_name>{tuple_delimiter}<entity_description>)

Fase 2. A partire dai tipi di entità trovati nella Fase 1, individuare tutte le caratteristiche che sono *evidenti dimensioni o proprietà* delle entità di quel tipo.
Per ogni caratteristica restituisci le seguenti informazioni:
- characteristic_name: il nome della caratteristica, in {iri_language}.
- characteristic_entity_type: il nome del tipo di entità, trovato nella Fase 1, a cui la caratteristica si riferisce
- characteristic_datatype: uno tra i seguenti tipi di dato: [{datatypes}]
- characteristic_description: una descrizione comprensibile della caratteristica trovata
Componi ciascuna caratteristica così: ("characteristic"{tuple_delimiter}<characteristic_name>{tuple_delimiter}<characteristic_entity_type>{tuple_delimiter}<characteristic_datatype>{tuple_delimiter}<characteristic_description>)

Fase 3. A partire dai tipi di entità trovati nella Fase 1, individuare tutte le coppie (sub_entity_type, super_entity_type) in cui il secondo tipo di entità è una *evidente generalizzazione* del primo.
Per ogni coppia di tipi di entità restituisci le seguenti informazioni:
- sub_entity_type: il nome del tipo di entità particolare, così come identificato nella Fase 1
- super_entity_type: il nome del tipo di entità generale, così come identificato nella Fase 1
Componi ciascuna generalizzazione così: ("subclass"{tuple_delimiter}<sub_entity_type>{tuple_delimiter}<super_entity_type>)

Fase 4. A partire dai tipi di entità trovati nella Fase 1, individuare tutte le coppie (source_entity_type, target_entity_type) che sono *evidentemente legati* uno con l'altro.
Per ogni coppia di tipi di entità restituisci le seguenti informazioni:
- relationship_name: il nome della relazione, in {iri_language}.
- source_entity_type: il nome del tipo di entità di partenza, così come identificato nella Fase 1
- target_entity_type: il nome del tipo di entità di arrivo, così come identificato nella Fase 1
- relationship_description: una spiegazione del motivo per cui ritieni che il tipo di entità di partenza e il tipo di entità di arrivo sono legati l'uno all'altro
- relationship_strength: un valore numerico che indica l'intensità del legame tra il tipo di entità di partenza e il tipo di entità di arrivo
Componi ciascuna relazione così: ("relationship"{tuple_delimiter}<relationship_name>{tuple_delimiter}<source_entity_type>{tuple_delimiter}<target_entity_type>{tuple_delimiter}<relationship_description>{tuple_delimiter}<relationship_strength>)

Fase 5. Restituisci il risultato in {language} come una lista dei tipi di entità, caratteristiche e relazioni trovate nella Fasi 1, 2 and 3. Usa **{record_delimiter}** come separatore degli elementi della lista.

Fase 6. Al termine, scrivi {completion_delimiter}

---Risultato---

Aggiungi di seguito ciò che hai trovato utilizzando lo stesso formato:
"""

# Sembra che alcuni tipi di entità non siano ancora state restituite.
    PROMPTS["entity_if_loop_extraction"] = """---Obiettivo---

Trova i tipi di entità che NON sono stati ancora restituiti.

---Risultato---

Rispondi soltanto con 'YES' o 'NO' se ci sono ancora tipi di entità da aggiungere."""

    PROMPTS["fail_response"] = (
        "Scusa, non sono in grado di soddisfare questa tua richiesta.[no-context]"
    )

    PROMPTS["null_response"] = (
        "Per poterti aiutare devi inserire una richiesta.[no-query]"
    )

    PROMPTS["repeat_response"] = (
        "Mi dispiace, non ho capito, potresti spiegarmi meglio, per favore?"
    )

    PROMPTS["find_doc_language"] = """---Role---

Sei un valido assistente in grado di rilevare la lingua in cui è scritto un testo

---Goal---

Restituisci solo la lingua in cui è scritto il seguente testo, senza altri commenti.
Indica la lingua in {language}.
######################
Testo:
{text}
######################
Risultato:
"""

    PROMPTS["label_translate"] = """---Role---

Sei un valido assistente in grado di tradurre un descrittore da una lingua ad un'altra

---Goal---

Traduci il seguente descrittore da {in_language} a {out_language}.
Restituisci solo il nuovo descrittore, senza altri commenti.
######################
Descrittore:
{descriptor}
######################
Risultato:
"""

    PROMPTS["rag_response"] = """---Role---

Sei un valido assistente in grado di rispondere ad una domanda sulla base del Knowledge Graph (KG) e degli estratti di documento di seguito forniti in formato JSON.

---Goal---

Genera una risposta pertinente alla domanda e alla conversazione in corso a partire dal seguente Knowledge Graph (KG) tenendo conto delle `Response Rules` indicate. Riassumi tutte le informazioni contenute nella Knowledge Base fornita, integrando anche le conoscenze generali pertinenti. Non includere informazioni non presenti nella Knowledge Base.

---Conversation History---
{history}

---Knowledge Graph---
{context_data}

---Response Rules---

- Lunghezza e formato della risposta: {response_type}
- Utilizza il formato markdown con gli appropriati titoli di sezione. 
- Rispondi nella stessa lingua della domanda.
- Mantieni la continuità con la conversazione in corso.
- Utilizza SEMPRE i punti elenco per restituire una lista di occorrenze.
- In un testo NON inserire il formato IRI per nominare un oggetto.
- Il valore della "Response" key è un testo.
- Esprimi le citazioni ad oggetti del Knowledge Graph come coppie <text citation> : <IRI object> nel valore della "References" key.
- Se non sai rispondere, dillo.
- Non inventare nulla. Non includere informazioni non fornite dalla Knowledge Base.
- Usa queste informazioni addizionali: {user_prompt}

######################
Risultato:"""

    PROMPTS["rag_RDF_example"] = """---Role---

Sei un valido assistente in grado di fornire un esempio concreto di oggetti di una ontologia.

---Goal---
Per ciascuna classe dell'ontologia presente in elenco definisci una istanza concreta assegnando a ogni proprietà della classe un valore concreto o una istanza concreta in base alla specifica della classe nell'ontologia.

---Response Rules---
- Lunghezza e formato della risposta: {response_type}
- Utilizza esclusivamente le IRI presenti nel namespaces dell'ontologia.
- Ogni nuovo oggetto deve avere un nome differente e diverso dal nome della relativa classe.
- Se è presente una relazione con un'altra classe, crea una sua istanza.
- Se è presente un attributo, assegna un valore coerente con il suo datatype.
- Mostra solo i namespaces strettamente necessari.
- Restituisci solo gli oggetti concreti in formato Turtle con il relativo namespaces, senza ulteriori specifiche, annotazioni, etichette o commenti.

---Class List---
{class_list}

---Ontology---
{context_data}

######################
Risultato:"""

    PROMPTS["rag_ontology_summary"] = """---Role---

Sei un valido assistente in grado di descrivere in modo completo il contenuto di una Ontologia di seguito definita in formato JSON.

---Goal---

Restituisci una completa descrizione del contenuto della Ontologia tenendo conto delle Response Rules. Usa tutte le informazioni contenute nella Ontologia, integrando anche le conoscenze generali pertinenti. Non includere informazioni non presenti nella Ontologia.

---Conversation History---
{history}

---Knowledge Graph and Document Chunks---
{context_data}

---Response Rules---
- Lunghezza e formato della risposta: {response_type}
- Quando descrivi una classe tieni conto delle sue relazioni di inclusione (subclass).
- Riferisci sempre con precisione gli elementi dell'ontologia. 
- Utilizza il formato markdown con gli appropriati titoli di sezione. 
- Rispondi in {language}.
- Se non sai rispondere, dillo.
- Non inventare nulla. Non includere informazioni non fornite dalla Ontologia.
- Usa queste informazioni addizionali: {user_prompt}

######################
Risultato:"""

    PROMPTS["keywords_extraction"] = """---Role---

Sei un valido assistente in grado di identificare le parole chiave (keywords) di una domanda dell'utente (query).

---Goal---

A partire dalla query produci due liste di keywords:
- "high-level keywords": include i verbi, gli avverbi e gli aggettivi presenti nella query
- "low-level keywords": include i nomi e gli aggettivi presenti nella query

Verifica il corretto uso delle parentesi quadre per delimitare l'elenco dei valori prodotti.

---Instructions---

- Restituisci le keywords in formato JSON senza aggiungere altri contenuti.
- Il formato JSON deve avere due keys:
  - "high_level_keywords"
  - "low_level_keywords"

######################
---Esempi---
######################
{examples}

#############################
---Real Data---
######################
Conversation History:
{history}

Query: {query}
######################
Restituisci il `Risultato` nella stessa lingua della `Query`.
Risultato:

"""

    PROMPTS["keywords_extraction_examples"] = [
    """Esempio 1:

Query: "Quali uccelli fanno il nido nei sottotetti ?"
################
Risultato:
{
    "high_level_keywords": ["fare", "nidificare", "accamparsi"],
    "low_level_keywords": [animale, uccello, nido, sottotetto, casa]
#############################""",
    """Esempio 2:

Query: "Dammi la percentuale di alberi da frutto presenti nel bosco di Chiaravalle"
################
Risultato:
{
    "high_level_keywords": ["essere presente", "partecipare", "far parte di", percentuale],
    "low_level_keywords": ["albero", "albero da frutto", "bosco"]
}
#############################""",
    """Esempio 3:

Query: "Quante persone maggiori di 18 anni possiedono una bicicletta rossa con manubrio nero ?"
################
Risultato:
{
    "high_level_keywords": ["possedere", "andare in bicicletta", maggiore, rosso, nero],
    "low_level_keywords": ["persona", "età", "bicicletta", "colore", "manubrio"]
}
#############################""",
]

elif PROMPTS_LANGUAGE == "English":

    PROMPTS["entity_extraction"] = """---Role---
You are a helpful assistant semantic analysis expert, who can identify the entity types and their relationships present in a text.
    
---Goal---
Given a text document that is potentially relevant to this activity, identify all entity types from the text with their own characteristics and all relationships among the identified entity types.

---Entity types and relationship response rules---
- Set singular names to entity types, characteristics and relationships, which must always be different from each other.
- Compose the names of entity types, characteristics, and relationships in {iri_format} mode without spaces.
- Return the names of entity types, characteristics and relationships in **{iri_language}**.
- Return descriptions of entity types, characteristics, and relationships in **{language}**.

---Steps---
1. Identify all entity types. For each identified entity types, extract the following information:
- entity_type_name: capitalized name of the entity type, in **{iri_language}**.
- entity_type_description: comprehensive description of the entity type's attributes and activities, in **{iri_language}**.
Format each entity type as ("entity_type"{tuple_delimiter}<entity_name>{tuple_delimiter}<entity_description>){record_delimiter}

2. From the entity types identified in step 1, identify all features that are a *clearly quality or measure* of the entities of the entity type.
For each feature extract the following information:
- characteristic_name: the name of the feature, in **{iri_language}**
- characteristic_entity_type: the name of the entity_type to whom the feature is referred to, as identified in step 1
- characteristic_datatype: the data type usually assumed by the feature, selected from the following types: {datatypes}
- characteristic_description: a comprehensive definition for the feature, in **{iri_language}**
Format each feature as ("characteristic"{tuple_delimiter}<characteristic_name>{tuple_delimiter}<characteristic_entity_type>{tuple_delimiter}<characteristic_datatype>{tuple_delimiter}<characteristic_description>){record_delimiter}

3. From the entity types identified in step 1, identify all ordered pairs of (sub_entity_type, super_entity_type) in which the former entity type is *clearly contained* in the latter.
For each pair of ordered entity types extract the following information:
- sub_entity_type: the name of the entity type content, as identified in step 1
- super_entity_type: the name of the entity type containing, as identified in step 1
Format each containment as ("subclass"{tuple_delimiter}<sub_entity_type>{tuple_delimiter}<super_entity_type>){record_delimiter}

4. From the entity types identified in step 1, identify all pairs of (source_entity_type, target_entity_type) that are *clearly related* to each other.
For each pair of related entity types, extract the following information:
- relationship_name: the name of the relationship, in **{iri_language}**
- source_entity_type: the name of the source entity type, as identified in step 1
- target_entity_type: the name of the target entity type, as identified in step 1
- relationship_description: explanation in **{language}** as to why you think the source entity type and the target entity type are related to each other
- relationship_strength: a numeric score indicating strength of the relationship between the source entity type and target entity type
Format each relationship as ("relationship"{tuple_delimiter}<relationship_name>{tuple_delimiter}<source_entity_type>{tuple_delimiter}<target_entity_type>{tuple_delimiter}<relationship_description>{tuple_delimiter}<relationship_strength>){record_delimiter}

5. Return output as a single list of all the entities, characteristics and relationships identified in steps 1, 2 and 3. Use **{record_delimiter}** as the list delimiter.

6. When finished, output {completion_delimiter}

#############################
---Real Data---
######################
Text:
{input_text}
######################
Output:
"""

    PROMPTS["entity_extraction_SC_examples"] = [
        """Example 1:

Text:
```A workplace is a physical space dedicated to the operational activities of an organization and therefore hosts its employees so that they can carry out their tasks using any tools made available to them in the place itself.
The workplace is also a public place since the latter, in order to provide services to the public, must necessarily provide for the presence of personnel assigned to such provision.
The workplace is characterized by a maximum number of employees who can be present at the same time during its operating hours.
```
######################
Output:
("entity_type"{tuple_delimiter}"Workplace"{tuple_delimiter}"A workplace is a physical space dedicated to the operational activities."){record_delimiter}
("entity_type"{tuple_delimiter}"Organization"{tuple_delimiter}"An organization is a group of people who work together in an organized way for a shared purpose."){record_delimiter}
("entity_type"{tuple_delimiter}"Employee"{tuple_delimiter}"Someone who is paid to work for someone else."){record_delimiter}
("entity_type"{tuple_delimiter}"Workstation"{tuple_delimiter}"An area where work of a particular nature is carried out."){record_delimiter}
("entity_type"{tuple_delimiter}"Public_place"{tuple_delimiter}"A place where people can ask and receive services."){record_delimiter}
("characteristic"{tuple_delimiter}"max_number_employees"{tuple_delimiter}"Workplace"{tuple_delimiter}"number"{tuple_delimiter}"Maximum number of employees who can operate at the same time in the workplace."){record_delimiter}
("characteristic"{tuple_delimiter}"opening_hour"{tuple_delimiter}"Workplace"{tuple_delimiter}"string"{tuple_delimiter}"Workplace opening hours."){record_delimiter}
("subclass"{tuple_delimiter}"Workplace"{tuple_delimiter}"Public_place"){record_delimiter}{completion_delimiter}
("relationship"{tuple_delimiter}"has_workplace"{tuple_delimiter}"Organization"{tuple_delimiter}"Workplace"{tuple_delimiter}"Links an organization to its workplace."{tuple_delimiter}8){record_delimiter}
("relationship"{tuple_delimiter}"has_organization"{tuple_delimiter}"Employee"{tuple_delimiter}"Organization"{tuple_delimiter}"Links an employee to the organization they work for."{tuple_delimiter}8){record_delimiter}
("relationship"{tuple_delimiter}"has_workstation"{tuple_delimiter}"Employee"{tuple_delimiter}"Workstation"{tuple_delimiter}"Links an employee to his workstation."{tuple_delimiter}7){record_delimiter}
#############################""",
        """Example 2:

Text:
```A bestowal is a role assumed by a person and relates to an assignment arranged by a public body through a specific assignment act.
The selection of the person suitable to take on a bestowal takes place through a competition procedure.
The bestowal has: a name, a description, a start date and an end date and a remuneration.
```
######################
Output:
("entity_type"{tuple_delimiter}"Bestowal"{tuple_delimiter}"A bestowal is a role assumed by a person and relates to an assignment arranged by a public body."){record_delimiter}
("entity_type"{tuple_delimiter}"Natural_person"{tuple_delimiter}"The entity who can assume a role assigned."){record_delimiter}
("entity_type"{tuple_delimiter}"Public_body"{tuple_delimiter}"The entity who can assign a bestowal."){record_delimiter}
("entity_type"{tuple_delimiter}"Assignment_act"{tuple_delimiter}"The legal instrument through which a bestowal is assigned."){record_delimiter}
("entity_type"{tuple_delimiter}"Competition_procedure"{tuple_delimiter}"The procedure by which the person suitable for the position is selected."){record_delimiter}
("characteristic"{tuple_delimiter}"name"{tuple_delimiter}"Bestowal"{tuple_delimiter}"string"{tuple_delimiter}"The name of the bestowal."){record_delimiter}
("characteristic"{tuple_delimiter}"description"{tuple_delimiter}"Bestowal"{tuple_delimiter}"string"{tuple_delimiter}"The description of the tasks related to the bestowal."){record_delimiter}
("characteristic"{tuple_delimiter}"start_date"{tuple_delimiter}"Bestowal"{tuple_delimiter}"datetime"{tuple_delimiter}"The start date of the assignment."){record_delimiter}
("characteristic"{tuple_delimiter}"end_date"{tuple_delimiter}"Bestowal"{tuple_delimiter}"datetime"{tuple_delimiter}"The end date of the assignment."){record_delimiter}
("characteristic"{tuple_delimiter}"remuneration"{tuple_delimiter}"Bestowal"{tuple_delimiter}"number"{tuple_delimiter}"The remuneration paid for the assignment."){record_delimiter}
("relationship"{tuple_delimiter}"has_bestowal"{tuple_delimiter}"Natural_person"{tuple_delimiter}"Bestowal"{tuple_delimiter}"Associates a natural person with an assigned role."{tuple_delimiter}8){record_delimiter}
("relationship"{tuple_delimiter}"bestowal_assigned_by"{tuple_delimiter}"Bestowal"{tuple_delimiter}"Public_body"{tuple_delimiter}"Associates the bestowal with the public body that assigned it."{tuple_delimiter}8){record_delimiter}
("relationship"{tuple_delimiter}"bestowal_assigned_with"{tuple_delimiter}"Bestowal"{tuple_delimiter}"Assignment_act"{tuple_delimiter}"Associates the bestowal with the act that legally established it."{tuple_delimiter}6){record_delimiter}
("relationship"{tuple_delimiter}"institution_issues_act"{tuple_delimiter}"Public_body"{tuple_delimiter}"Assignment_act"{tuple_delimiter}"Associates the public body that issued the act with the act itself."{tuple_delimiter}6){record_delimiter}
("relationship"{tuple_delimiter}"has_competition_winner"{tuple_delimiter}"Competition_procedure"{tuple_delimiter}"Natural_person"{tuple_delimiter}"Links the competition procedure with the winner natural person."{tuple_delimiter}7){record_delimiter}{completion_delimiter}
#############################""",
        """Example 3:
Text:
```A food chain is characterized by the food product to which it gives rise, meaning, according to European legislation, 'any substance or product, whether processed, partially processed or unprocessed, intended to be ingested, or reasonably expected to be ingested, by humans'.
Considering the food products available on the market, they are classified according to the product category to which they belong. These categories are hierarchically ordered and group together all the products that can be marketed, therefore not only food products but also products that are not intended for human consumption as well as the so-called "surpluses", i.e. food products that have lost their suitability for their intended use but are still usable for human consumption, before becoming waste, also classified by appropriate categories.
In general these are all types of product or rather quantities of aliquots of matter.
```
######################
Output:
("entity_type"{tuple_delimiter}"Product"{tuple_delimiter}"Aliquots of matter."){record_delimiter}
("entity_type"{tuple_delimiter}"Food_product"{tuple_delimiter}"A product, whether processed, partially processed or unprocessed, intended to be ingested, or reasonably expected to be ingested, by humans."){record_delimiter}
("entity_type"{tuple_delimiter}"No_food_product"{tuple_delimiter}"Product not intended for human consumption."){record_delimiter}
("entity_type"{tuple_delimiter}"Surplus"{tuple_delimiter}"Food product which has lost its suitability for its intended use but which is still usable for human consumption."){record_delimiter}
("entity_type"{tuple_delimiter}"Waste"{tuple_delimiter}"Product destined for disposal because it is no longer edible."){record_delimiter}
("entity_type"{tuple_delimiter}"Category"{tuple_delimiter}"Scope of relevance of an object or product."){record_delimiter}
("entity_type"{tuple_delimiter}"Product_category"{tuple_delimiter}"Category of products that can be marketed."){record_delimiter}
("entity_type"{tuple_delimiter}"Waste_category"{tuple_delimiter}"Category of products intended for disposal as waste."){record_delimiter}
("characteristic"{tuple_delimiter}"quantity"{tuple_delimiter}"Product"{tuple_delimiter}"number"{tuple_delimiter}"Quantità di aliquota di materia presente in un prodotto."){record_delimiter}
("characteristic"{tuple_delimiter}"product_name"{tuple_delimiter}"Product"{tuple_delimiter}"string"{tuple_delimiter}"Product identification name."){record_delimiter}
("characteristic"{tuple_delimiter}"category_name"{tuple_delimiter}"Category"{tuple_delimiter}"string"{tuple_delimiter}"Category identification name."){record_delimiter}
("subclass"{tuple_delimiter}"Food_product"{tuple_delimiter}"Product"){record_delimiter}
("subclass"{tuple_delimiter}"No_food_product"{tuple_delimiter}"Product"){record_delimiter}
("subclass"{tuple_delimiter}"Surplus"{tuple_delimiter}"Product"){record_delimiter}
("subclass"{tuple_delimiter}"Waste"{tuple_delimiter}"Product"){record_delimiter}
("subclass"{tuple_delimiter}"Product_category"{tuple_delimiter}"Category"){record_delimiter}
("subclass"{tuple_delimiter}"Waste_category"{tuple_delimiter}"Category"){record_delimiter}
("relationship"{tuple_delimiter}"has_category"{tuple_delimiter}"Product"{tuple_delimiter}"Category"{tuple_delimiter}"Link between a product and its category."{tuple_delimiter}8){record_delimiter}
("relationship"{tuple_delimiter}"has_subcategory"{tuple_delimiter}"Category"{tuple_delimiter}"Category"{tuple_delimiter}"Hierarchical relationship between categories."{tuple_delimiter}5){record_delimiter}{completion_delimiter}
#############################""",
    ]

    PROMPTS["entity_extraction_CC_examples"] = [
        """Example 1:

Text:
```A workplace is a physical space dedicated to the operational activities of an organization and therefore hosts its employees so that they can carry out their tasks using any tools made available to them in the place itself.
The workplace is also a public place since the latter, in order to provide services to the public, must necessarily provide for the presence of personnel assigned to such provision.
The workplace is characterized by a maximum number of employees who can be present at the same time during its operating hours.
```
######################
Output:
("entity_type"{tuple_delimiter}"Workplace"{tuple_delimiter}"A workplace is a physical space dedicated to the operational activities."){record_delimiter}
("entity_type"{tuple_delimiter}"Organization"{tuple_delimiter}"An organization is a group of people who work together in an organized way for a shared purpose."){record_delimiter}
("entity_type"{tuple_delimiter}"Employee"{tuple_delimiter}"Someone who is paid to work for someone else."){record_delimiter}
("entity_type"{tuple_delimiter}"Workstation"{tuple_delimiter}"An area where work of a particular nature is carried out."){record_delimiter}
("entity_type"{tuple_delimiter}"PublicPlace"{tuple_delimiter}"A place where people can ask and receive services."){record_delimiter}
("characteristic"{tuple_delimiter}"maxNumberEmployees"{tuple_delimiter}"Workplace"{tuple_delimiter}"number"{tuple_delimiter}"Maximum number of employees who can operate at the same time in the workplace."){record_delimiter}
("characteristic"{tuple_delimiter}"openingHour"{tuple_delimiter}"Workplace"{tuple_delimiter}"string"{tuple_delimiter}"Workplace opening hours."){record_delimiter}
("subclass"{tuple_delimiter}"Workplace"{tuple_delimiter}"PublicPlace"){record_delimiter}{completion_delimiter}
("relationship"{tuple_delimiter}"hasWorkplace"{tuple_delimiter}"Organization"{tuple_delimiter}"Workplace"{tuple_delimiter}"Links an organization to its workplace."{tuple_delimiter}8){record_delimiter}
("relationship"{tuple_delimiter}"hasOrganization"{tuple_delimiter}"Employee"{tuple_delimiter}"Organization"{tuple_delimiter}"Links an employee to the organization they work for."{tuple_delimiter}8){record_delimiter}
("relationship"{tuple_delimiter}"hasWorkstation"{tuple_delimiter}"Employee"{tuple_delimiter}"Workstation"{tuple_delimiter}"Links an employee to his workstation."{tuple_delimiter}7){record_delimiter}
#############################""",
        """Example 2:

Text:
```A bestowal is a role assumed by a person and relates to an assignment arranged by a public body through a specific assignment act.
The selection of the person suitable to take on a bestowal takes place through a competition procedure.
The bestowal has: a name, a description, a start date and an end date and a remuneration.
```
######################
Output:
("entity_type"{tuple_delimiter}"Bestowal"{tuple_delimiter}"A bestowal is a role assumed by a person and relates to an assignment arranged by a public body."){record_delimiter}
("entity_type"{tuple_delimiter}"NaturalPerson"{tuple_delimiter}"The entity who can assume a role assigned."){record_delimiter}
("entity_type"{tuple_delimiter}"PublicBody"{tuple_delimiter}"The entity who can assign a bestowal."){record_delimiter}
("entity_type"{tuple_delimiter}"AssignmentAct"{tuple_delimiter}"The legal instrument through which a bestowal is assigned."){record_delimiter}
("entity_type"{tuple_delimiter}"CompetitionProcedure"{tuple_delimiter}"The procedure by which the person suitable for the position is selected."){record_delimiter}
("characteristic"{tuple_delimiter}"name"{tuple_delimiter}"Bestowal"{tuple_delimiter}"string"{tuple_delimiter}"The name of the bestowal."){record_delimiter}
("characteristic"{tuple_delimiter}"description"{tuple_delimiter}"Bestowal"{tuple_delimiter}"string"{tuple_delimiter}"The description of the tasks related to the bestowal."){record_delimiter}
("characteristic"{tuple_delimiter}"startDate"{tuple_delimiter}"Bestowal"{tuple_delimiter}"datetime"{tuple_delimiter}"The start date of the assignment."){record_delimiter}
("characteristic"{tuple_delimiter}"endDate"{tuple_delimiter}"Bestowal"{tuple_delimiter}"datetime"{tuple_delimiter}"The end date of the assignment."){record_delimiter}
("characteristic"{tuple_delimiter}"remuneration"{tuple_delimiter}"Bestowal"{tuple_delimiter}"number"{tuple_delimiter}"The remuneration paid for the assignment."){record_delimiter}
("relationship"{tuple_delimiter}"hasBestowal"{tuple_delimiter}"NaturalPerson"{tuple_delimiter}"Bestowal"{tuple_delimiter}"Associates a natural person with an assigned role."{tuple_delimiter}8){record_delimiter}
("relationship"{tuple_delimiter}"bestowalAssignedBy"{tuple_delimiter}"Bestowal"{tuple_delimiter}"PublicBody"{tuple_delimiter}"Associates the bestowal with the public body that assigned it."{tuple_delimiter}8){record_delimiter}
("relationship"{tuple_delimiter}"bestowalAssignedWith"{tuple_delimiter}"Bestowal"{tuple_delimiter}"AssignmentAct"{tuple_delimiter}"Associates the bestowal with the act that legally established it."{tuple_delimiter}6){record_delimiter}
("relationship"{tuple_delimiter}"institutionIssuesAct"{tuple_delimiter}"PublicBody"{tuple_delimiter}"AssignmentAct"{tuple_delimiter}"Associates the public body that issued the act with the act itself."{tuple_delimiter}6){record_delimiter}
("relationship"{tuple_delimiter}"hasCompetitionWinner"{tuple_delimiter}"CompetitionProcedure"{tuple_delimiter}"NaturalPerson"{tuple_delimiter}"Links the competition procedure with the winner natural person."{tuple_delimiter}7){record_delimiter}{completion_delimiter}
#############################""",
        """Example 3:
Text:
```A food chain is characterized by the food product to which it gives rise, meaning, according to European legislation, 'any substance or product, whether processed, partially processed or unprocessed, intended to be ingested, or reasonably expected to be ingested, by humans'.
Considering the food products available on the market, they are classified according to the product category to which they belong. These categories are hierarchically ordered and group together all the products that can be marketed, therefore not only food products but also products that are not intended for human consumption as well as the so-called "surpluses", i.e. food products that have lost their suitability for their intended use but are still usable for human consumption, before becoming waste, also classified by appropriate categories.
In general these are all types of product or rather quantities of aliquots of matter.
```
######################
Output:
("entity_type"{tuple_delimiter}"Product"{tuple_delimiter}"Aliquots of matter."){record_delimiter}
("entity_type"{tuple_delimiter}"FoodProduct"{tuple_delimiter}"A product, whether processed, partially processed or unprocessed, intended to be ingested, or reasonably expected to be ingested, by humans."){record_delimiter}
("entity_type"{tuple_delimiter}"NoFoodProduct"{tuple_delimiter}"Product not intended for human consumption."){record_delimiter}
("entity_type"{tuple_delimiter}"Surplus"{tuple_delimiter}"Food product which has lost its suitability for its intended use but which is still usable for human consumption."){record_delimiter}
("entity_type"{tuple_delimiter}"Waste"{tuple_delimiter}"Product destined for disposal because it is no longer edible."){record_delimiter}
("entity_type"{tuple_delimiter}"Category"{tuple_delimiter}"Scope of relevance of an object or product."){record_delimiter}
("entity_type"{tuple_delimiter}"ProductCategory"{tuple_delimiter}"Category of products that can be marketed."){record_delimiter}
("entity_type"{tuple_delimiter}"WasteCategory"{tuple_delimiter}"Category of products intended for disposal as waste."){record_delimiter}
("characteristic"{tuple_delimiter}"quantity"{tuple_delimiter}"Product"{tuple_delimiter}"number"{tuple_delimiter}"Quantità di aliquota di materia presente in un prodotto."){record_delimiter}
("characteristic"{tuple_delimiter}"productName"{tuple_delimiter}"Product"{tuple_delimiter}"string"{tuple_delimiter}"Product identification name."){record_delimiter}
("characteristic"{tuple_delimiter}"categoryName"{tuple_delimiter}"Category"{tuple_delimiter}"string"{tuple_delimiter}"Category identification name."){record_delimiter}
("subclass"{tuple_delimiter}"FoodProduct"{tuple_delimiter}"Product"){record_delimiter}
("subclass"{tuple_delimiter}"NoFoodProduct"{tuple_delimiter}"Product"){record_delimiter}
("subclass"{tuple_delimiter}"Surplus"{tuple_delimiter}"Product"){record_delimiter}
("subclass"{tuple_delimiter}"Waste"{tuple_delimiter}"Product"){record_delimiter}
("subclass"{tuple_delimiter}"ProductCategory"{tuple_delimiter}"Category"){record_delimiter}
("subclass"{tuple_delimiter}"WasteCategory"{tuple_delimiter}"Category"){record_delimiter}
("relationship"{tuple_delimiter}"hasCategory"{tuple_delimiter}"Product"{tuple_delimiter}"Category"{tuple_delimiter}"Link between a product and its category."{tuple_delimiter}8){record_delimiter}
("relationship"{tuple_delimiter}"hasSubcategory"{tuple_delimiter}"Category"{tuple_delimiter}"Category"{tuple_delimiter}"Hierarchical relationship between categories."{tuple_delimiter}5){record_delimiter}{completion_delimiter}
#############################""",
    ]

    PROMPTS[
        "summarize_entity_descriptions"
    ] = """You are a helpful assistant responsible for generating a comprehensive summary of the data provided below.
Given one or more entities, and a list of descriptions, all related to the same entity type or group of entities.
Please concatenate all of these into a single, comprehensive description. Make sure to include information collected from all the descriptions.
If the provided descriptions are contradictory, please resolve the contradictions and provide a single, coherent summary.
Make sure it is written in third person, and include the entity type names so we the have full context.
Use {language} as output language.

#######
-Data-
Entity Types: {entity_name}
Description List: {description_list}
#######
Output:
"""

    PROMPTS[
        "entity_continue_extraction"
    ] = """MANY entities and relationships were missed in the last extraction.

---Remember Steps---

-Steps-
1. Identify all entity types. For each identified entity types, extract the following information:
- entity_type_name: Name of the entity type, use same language as input text. If English, capitalized the name.
- entity_type_description: Comprehensive description of the entity type's attributes and activities
Format each entity type as ("entity_type"{tuple_delimiter}<entity_name>{tuple_delimiter}<entity_description>)

2. From the entity types identified in step 1, identify all characteristics that are a *clearly quality or measure* of the entities of the entity type.
For each characteristic extract the following information:
- characteristic_name: name of the characteristic
- characteristic_entity_type: name of the entity_type to whom the characteristic is referred to, as identified in step 1
- characteristic_datatype: One of the following data types: [{datatypes}]
- characteristic_description: definition of the entity type's characteristic
Format each characteristic as ("characteristic"{tuple_delimiter}<characteristic_name>{tuple_delimiter}<characteristic_entity_type>{tuple_delimiter}<characteristic_datatype>{tuple_delimiter}<characteristic_description>)

3. From the entity types identified in step 1, identify all ordered pairs of (sub_entity_type, super_entity_type) in which the former entity type is *clearly contained* in the latter.
For each pair of ordered entity types extract the following information:
- sub_entity_type: name of the entity type content, as identified in step 1
- super_entity_type: name of the entity type containing, as identified in step 1
Format each containment as ("subclass"{tuple_delimiter}<sub_entity_type>{tuple_delimiter}<super_entity_type>)

4. From the entity types identified in step 1, identify all pairs of (source_entity_type, target_entity_type) that are *clearly related* to each other.
For each pair of related entity types, extract the following information:
- relationship_name: name of the relationship
- source_entity_type: name of the source entity type, as identified in step 1
- target_entity_type: name of the target entity type, as identified in step 1
- relationship_description: explanation as to why you think the source entity type and the target entity type are related to each other
- relationship_strength: a numeric score indicating strength of the relationship between the source entity type and target entity type
Format each relationship as ("relationship"{tuple_delimiter}<relationship_name>{tuple_delimiter}<source_entity_type>{tuple_delimiter}<target_entity_type>{tuple_delimiter}<relationship_description>{tuple_delimiter}<relationship_strength>)

5. Return output in {language} as a single list of all the entities, characteristics and relationships identified in steps 1, 2 and 3. Use **{record_delimiter}** as the list delimiter.

6. When finished, output {completion_delimiter}

---Output---

Add them below using the same format:
"""

    PROMPTS["find_doc_language"] = """---Role---

You are a helpful assistant detecting the language in which a text is written.

---Goal---

Return only the language in which the following text is written, without any other comments.
Point out the language in {language}.
######################
Text:
{text}
######################
Output:
"""

    PROMPTS["label_translate"] = """---Role---

You are a helpful assistant responsible for translate a descriptor from one language to another.

---Goal---

Translate the following descriptor from {in_language} to {out_language}.
Return only the new descriptor, without any other comments.
######################
Descriptor:
{descriptor}
######################
Output:
"""

    PROMPTS["null_response"] = (
        "To help you, you must submit a request.[no-query]"
    )

    PROMPTS["repeat_response"] = (
        "Sorry I didn't understand, can you please explain better?"
    )

    PROMPTS["rag_response"] = """---Role---

You are a helpful assistant responding to user query about Knowledge Graph and Document Chunks provided in JSON format below.

---Goal---

Generate a concise response based on Knowledge Base and follow Response Rules, considering both the conversation history and the current query. Summarize all information in the provided Knowledge Base, and incorporating general knowledge relevant to the Knowledge Base. Do not include information not provided by Knowledge Base.

---Conversation History---
{history}

---Knowledge Graph and Document Chunks---
{context_data}

---Response Rules---
- Target format and length: {response_type}
- Use markdown formatting with appropriate section headings
- Please respond in the same language as the user's question.
- Ensure the response maintains continuity with the conversation history.
- ALWAYS return lists as bulleted lists.
- Do NOT enter IRI in the "Response" key-value.
- The "Response" key-value is a text.
- Enter all citations to Knowledge Graph objects as <text citation> : <IRI object> pairs in the "References" key-value.
- If you don't know the answer, just say so.
- Do not make anything up. Do not include information not provided by the Knowledge Base.
- Addtional user prompt: {user_prompt}

######################
Output:
"""

    PROMPTS["rag_RDF_example"] = """---Role---

You are a helpful assistant providing concrete objects of an ontology.

---Goal---
For each class in a list belonging to the ontology, create a class object assigned each class property a concrete value or a concrete object according to the class specification. 

---Response Rules---
- Target format and length: {response_type}
- Use only the IRI namespaces defined in the ontology section.
- Each new object has its own name different from the class name.
- If there are relationships with other classes, assign them value as well.
- If there are attributes, assign the value according with the datatype.
- Show only the strictly necessary namespaces.
- Return only the concrete objects with namespaces section in turtle format without specification, annotation, label or comment.

---Class List---
{class_list}

---Ontology---
{context_data}

######################
Output:
"""

    PROMPTS["rag_ontology_summary"] = """---Role---

You are a helpful assistant in explaining the content of a Knowledge Base provided in JSON format below.

---Goal---

Generate a complete description of the Knowledge Base content following the Response Rules. Use all information in the provided Knowledge Base, and incorporating general knowledge relevant to the Knowledge Base. Do not include information not provided by Knowledge Base.

---Conversation History---
{history}

---Knowledge Graph and Document Chunks---
{context_data}

---Response Rules---
- Target format and length: {response_type}
- When describing a class, take into account its inclusion relations (subclass).
- Always accurately reference the elements of the ontology.
- Refer to the Knowledge Base as ontology.
- Use markdown formatting with appropriate section headings.
- Please respond in {language}.
- If you don't know the answer, just say so.
- Do not make anything up. Do not include information not provided by the Knowledge Base.
- Addtional user prompt: {user_prompt}

######################
Output:"""

