package main

import (
	"fmt"
	"os"

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

	fmt.Println("GO_OK")
}
