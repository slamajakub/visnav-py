#!/bin/bash
WIN="11 21 31"
sigma_col="10 30 50"
sigma_space="10 30 50"
sigma_coeff="10 30 50"

for w in $WIN; do
    for c in $sigma_col; do
        for s in $sigma_space; do
            for coeff in $sigma_coeff; do
                sudo DRI_PRIME=1 python3 src/batch1.py didy1w akaze+smn 10 False True $w $c $s $coeff >> outputs/output.txt
            done
        done
    done
done
