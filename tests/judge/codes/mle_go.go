package main

func main() {
	chunks := make([][]byte, 0, 70)
	for i := 0; i < 70; i++ {
		chunk := make([]byte, 16*1024*1024)
		for j := 0; j < len(chunk); j += 4096 {
			chunk[j] = byte((i + j) & 255)
		}
		chunks = append(chunks, chunk)
	}

	if len(chunks) != 70 {
		panic("allocation failed")
	}
}
