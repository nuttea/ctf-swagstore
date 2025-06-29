package main

import (
	"math/rand"
	"testing"
)

func TestGetRandomLetterCodeIncludesZ(t *testing.T) {
	rand.Seed(1)
	seenZ := false
	for i := 0; i < 1000; i++ {
		c := getRandomLetterCode()
		if c < 65 || c > 90 {
			t.Fatalf("generated code %d out of range", c)
		}
		if c == 90 {
			seenZ = true
			break
		}
	}
	if !seenZ {
		t.Errorf("did not generate letter code for Z within 1000 iterations")
	}
}
