# **<font color="red">Self - Attention in NLP</font>**
Last Updated : 23 Aug, 2025

In Transformer models, self-attention allows the model to look at all words in a sentence at once but it doesn’t naturally understand the order of those words. This is a problem because word order matters in language. To solve this Transformers use positional embeddings extra information added to each word that tells the model where it appears in the sentence. This helps the model understand both the meaning of each word and its position so it can process sentences more effectively.

## **<font color="blue">Attention in NLP</font>**

The goal of self attention mechanism is to improve performance of traditional models such as encoder decoder models used in RNNs (Recurrent Neural Networks).
In traditional encoder decoder models input sequence is compressed into a single fixed-length vector which is then used to generate the output.
This works well for short sequences but struggles with long ones because important information can be lost when compressed into a single vector.
To overcome this problem self attention mechanism was introduced.

### **<font color="green">Encoder Decoder Model</font>**
An encoder decoder model is used in machine learning tasks that involve sequences like translating sentences, generating text or creating captions for images. Here's how it works:

**Encoder**: It takes the input sequence like sentences and processes them. It converts input into a fixed size summary called a latent vector or context vector. This vector holds all the important information from the input sequence.
**Decoder**: It then uses this summary to generate an output sequence such as a translated sentence. It tries to reconstruct the desired output based on the encoded information.

## **<font color="blue">Attention Layer in Transformer</font>**

**Input Embedding**: Input text like a sentences are first converted into embeddings. These are vector representations of words in a continuous space.
**Positional Encoding**: Since Transformer doesn’t process words in a sequence like RNNs positional encodings are added to the input embeddings and these encode the position of each word in the sentence.
**Multi Head Attention**: In this multiple attention heads are applied in parallel to process different part of sequences simultaneously. Each head finds the attention scores based on queries (Q), keys (K) and values (V) and adds information from different parts of input.
**Add and Norm**: This layer helps in residual connections and layer normalization. This helps to avoid vanishing gradient problems and ensures stable training.
**Feed Forward**: After attention output is passed through a feed forward neural network for further transformation.
**Masked Multi Head Attention for the Decoder**: This is used in the decoder and ensures that each word can only attend to previous words in the sequence not future ones.
**Output Embedding**: Finally transformed output is mapped to a final output space and processed by softmax function to generate output probabilities.

## **<font color="blue">Self Attention Mechanism</font>**

This mechanism captures long range dependencies by calculating attention between all words in the sequence and helping the model to look at the entire sequence at once. Unlike traditional models that process words one by one it helps the model to find which words are most relevant to each other helpful for tasks like translation or text generation.