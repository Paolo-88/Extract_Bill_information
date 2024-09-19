abbiamo due file finali:

* 1_extract_from_picture_with_debug.py --> estrae i dati di piu fatture salvando anche i file intermedi, extracted e formatted, in file txt. 
poi li salva successivamente in un csv.


*  2_extract_from_picture_with_rename.py  --> estrae i dati di piu fatture senza salvare i file intermedi. 
Vediamo il risultato finale solo nel file csv.




*  2_extract_from_picture_with_rename_new_prompt.py  --> lo stesso del precedente solo che ho rimosso qualche frase dal prompt che organizza e ordina i dati.
Ovvero quello che vediamo in formatted.txt. Questo ha portato un miglioramento nella ricerca del dato.


*  extract_from_picture_with_gemma2_new_prompt.py --> ho effettuato delle sostiutuzioni per cercare di migliorare l'estrazione di qualche campo come 
SUBTOTAL o IVA o CIF NIF compañia --> ho provato anche il modello gemma2 --> risultato prossimo all'80% (BENE)

** extract_from_picture_with_gemma2_new_prompt_link.py --> ho aggiunto il link al pdf rinominato. Cosi da averlo a portata di mano per il controllo.
