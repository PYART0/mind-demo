ngram-count -text train.txt  -order 4 -write count.txt
ngram-count -read count.txt -order 4 -lm train.lm -interpolate -kndiscount
