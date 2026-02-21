package main

import (
	"fmt"
	"os"
	"strconv"
	"time"

	"github.com/benbjohnson/immutable"
	"github.com/emirpasic/gods/lists/arraylist"
	gostlvec "github.com/liyue201/gostl/ds/vector"
	"github.com/monkukui/ac-library-go/dsu"
	"golang.org/x/exp/slices"
	"gonum.org/v1/gonum/mat"
)

func check(cond bool, msg string) {
	if !cond {
		fmt.Fprintln(os.Stderr, msg)
		os.Exit(1)
	}
}

func main() {
	// gods - arraylist
	list := arraylist.New()
	list.Add(3, 1, 2)
	list.Sort(func(a, b interface{}) int { return a.(int) - b.(int) })
	v0, _ := list.Get(0)
	check(v0.(int) == 1, "gods arraylist sort check failed")

	// gonum - matrix determinant
	m := mat.NewDense(2, 2, []float64{1, 2, 3, 4})
	det := mat.Det(m)
	check(det < -1.9 && det > -2.1, "gonum determinant check failed")

	// gostl - vector
	vec := gostlvec.New[int]()
	vec.PushBack(10)
	vec.PushBack(20)
	check(vec.Size() == 2, "gostl vector check failed")

	// immutable - map
	b := immutable.NewMapBuilder[string, int](nil)
	b.Set("x", 42)
	im := b.Map()
	val, ok := im.Get("x")
	check(ok && val == 42, "immutable map check failed")

	// golang.org/x/exp - slices
	s := []int{3, 1, 2}
	slices.Sort(s)
	check(s[0] == 1 && s[1] == 2 && s[2] == 3, "x/exp slices sort check failed")

	// ac-library-go - dsu
	d := dsu.New(4)
	d.Merge(0, 1)
	check(d.Same(0, 1), "ac-library-go dsu check failed")
	check(!d.Same(0, 2), "ac-library-go dsu negative check failed")

	heavySeconds := 2
	if raw := os.Getenv("HEAVY_SECONDS"); raw != "" {
		n, err := strconv.Atoi(raw)
		check(err == nil && n >= 1, "invalid HEAVY_SECONDS")
		heavySeconds = n
	}

	deadline := time.Now().Add(time.Duration(heavySeconds) * time.Second)
	var acc uint64 = 1
	for time.Now().Before(deadline) {
		for i := uint64(1); i <= 100000; i++ {
			acc = (acc*1103515245 + i + 12345) % 1000000007
		}
	}

	fmt.Println("GO_OK")
	fmt.Println("GO_HEAVY_OK", acc)
}
