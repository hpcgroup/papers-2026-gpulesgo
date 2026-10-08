# Talk Script: Accelerating Production-Scale LES of Wind Farms on GPUs

About 16 minutes at a relaxed pace. One section per slide. Stage cues are in *italics*.

---

## 1. Title

Hi everyone. I'm Cunyang Wei from the University of Maryland. Today I'll show how we ported LESGO, a wind farm simulation code, to GPUs, and why the hard part wasn't the math. It was moving data. This is joint work with Wenyuan Chen, Abhinav Bhatele, Charles Meneveau, and Zheng Li.

## 2. Why Accelerate Wind-Farm LES?

Let's start with why this matters. In a big wind farm, turbines sit in each other's wakes, and that costs 10 to 20 percent of the farm's power. To study it, we need tens of turbines, kilometers of turbulent air, and hours of physical time.

Large eddy simulation, or LES, is the standard tool here. LESGO is a widely used open source LES code. It's pseudo spectral, so it's very accurate per grid point.

*(point to the figure)* This is our benchmark: 60 turbines on a 604 million cell grid. You can see the blue wakes trailing behind each turbine. The catch is time. A production run needs hundreds of thousands of steps, and on CPUs each step takes 6.5 seconds. That's days per run.

## 3. One LESGO Time Step

Here's what one time step looks like. It's the main loop from our paper.

First, Derivatives computes velocity gradients. It uses 2D FFTs in the horizontal plane and finite differences in z.

Then SGS models the turbulence we can't resolve. Every fifth step, it filters 21 fields and traces values back along particle paths. That's the most irregular code in the solver.

Convection handles the nonlinear term. It does a lot of FFTs.

Turbines uses an actuator line model. It samples velocity at thousands of blade points, looks up lift and drag, and spreads the forces back onto the grid.

Finally, Pressure solves a Poisson equation. FFTs split it into about 590 thousand small tridiagonal systems along z.

*(point to the tags)* These tags show which optimization targets each routine. I'll come back to them.

## 4. 1D Slab Decomposition Hits a CPU Ceiling

On CPUs, LESGO splits the domain into horizontal slabs, one per process. That keeps the FFTs local, which is nice. But every tridiagonal system runs through all the processes along z. So the pressure solve becomes a chain.

*(point to the plot)* And the scaling is bad. Going from 16 to 64 cores gives you just 1.08 times. At 128 processes, a node runs out of memory. Four full nodes only get you 2.1 times over one node, and we're stuck at 6.5 seconds per step. That's the ceiling we wanted to break.

## 5. Porting the Kernels with OpenACC

So we moved to GPUs with OpenACC. We picked directives over a CUDA rewrite because LESGO is a big, validated Fortran code, and its users keep extending it in Fortran.

*(point to the code)* Porting the compute is honestly the easy part. Each kernel is a loop over x, y, and z, and the iterations don't depend on each other. So we add one directive. collapse(3) gives every grid cell its own GPU thread. default(present) throws an error if an array isn't on the GPU, so nothing gets copied behind our back. And FFTW calls become batched cuFFT on the same stream as the loops, so there's no host sync between them.

Best of all, there's still one source tree. The CPU build works just like before.

## 6. Computation Is Easy, Data Placement Is Not

The hard part is deciding where the data lives. Every array in LESGO holds a full 3D field. So any transfer you don't need moves a whole field across PCIe.

Directive based ports usually pick one of three strategies. One, mirror every array on the GPU. Two, let CUDA managed memory move pages around for you. Three, control residency yourself, array by array and access by access.

The first two take very little code, so we tried them first.

## 7. Strategy 1: Array Mirroring

Here's mirroring on a small test case. *(point to the blue sliver)* The GPU is busy for 13 milliseconds out of a 220 millisecond step. It's idle 94 percent of the time.

Why? Some routines run faster on the CPU, so they stay there. Every time one of them reads solver data, a full field crosses PCIe. The biggest cost is twelve full field syncs, 420 megabytes per step. The host only needs about 5 of those megabytes.

Mirroring also eats memory. LESGO has dozens of big fields plus padded FFT buffers. Copying arrays that no kernel even reads means you need more GPUs for the same grid.

## 8. Strategy 2: CUDA Managed Memory

Managed memory is even easier. It's one compiler flag.

But on our production case with 16 GPUs, Nsight shows page faults and on demand migration stalling everything. *(point to the orange bar)* The pressure solve alone takes almost a second per step, and it's mostly page faults. On top of that, the traffic is hidden from you, so there's nothing to tune.

*(point to the box)* Both strategies fail for the same reason. Once the kernels move to the GPU, the routines left on the host still pull full fields across. To fix that, we need fine grained control. That's strategy three.

## 9. Consumer-Driven Explicit Residency

Here's how strategy three works. First, the GPU always holds the main copy of every field. We declare every persistent array on the device, and every kernel checks the data is already there. Host code only touches solver data at specific spots. We call them coupling points.

Then, for each coupling point, we ask what the host actually reads. Is it a scalar, a column, a plane, or a chunk of the volume? How often does it run? Does it read, write, or both?

That gives us four treatments, and we try them in order. Gate skips the transfer when the host code doesn't run. Relocate moves that code to the GPU, so the transfer goes away. Slice keeps the code on the CPU but sends only the piece it touches. And overlap hides whatever's left behind GPU work.

## 10. Nine Coupling-Point Classes, Four Treatments

We went through every coupling point in LESGO and found nine classes. This table lists each one, what a naive port pays per step, and the fix.

You can see most of the big transfers are either relocated or sliced down to almost nothing. After all this, a steady state step moves under 4 megabytes across PCIe in total. We think these classes show up in most pseudo spectral codes, so you can use this as a porting checklist.

## 11. Example: Slicing the Pressure DC Mode

Let me show one example. In the pressure solve, the GPU handles all the wavenumber modes in one batched call, except one. The zero mode is special. It needs a short serial loop along z, and one CPU core runs that faster than the GPU.

*(point to the top code)* Our first port copied the whole pressure field to the host and back. That's three 34 megabyte round trips every step, just for one column.

*(point to the bottom code)* With slicing, we copy only that column, about one kilobyte each way. Same math, same answer, almost no traffic.

## 12. Opt. 1: Chunk Pipelining the Thomas Solve

Now, three optimizations. First, the pressure solve. We have about 590 thousand tridiagonal systems, and each one spans all 16 processes. The Thomas algorithm sweeps down and back up, so in the naive version, *(point to part a)* each process sits and waits for the one above it.

But the systems are independent. So we cut them into chunks. *(point to part b)* A process finishes chunk one, passes it down, and starts chunk two right away. The last process can turn around each chunk immediately.

The inner loops don't change at all, so the results match the original exactly. This makes the whole step 1.9 times faster.

## 13. Opt. 2: Batching Many Small Work Items

Second, batching. Some work comes in pieces that are too small to keep a GPU busy.

For the turbines, the naive version handled each turbine on its own: its own uploads, its own launches, its own reductions. That's over a thousand MPI_Allreduce calls per process, per step. Now all the blade data lives on the GPU. One kernel samples every blade point, one kernel spreads every force, and one packed Allreduce does all the reductions.

The LASD model had the same problem with thousands of tiny FFTs, one per plane. We turned the 2D scratch arrays into 3D ones, so one cuFFT call covers every level at once.

Batching the turbines alone gives 1.6 times. As a bonus, removing allocations from the time loop sped up the other stages by 15 to 18 percent.

## 14. Opt. 3: Heterogeneous CPU–GPU Execution

Third, some work just belongs on the CPU. Blade force evaluation has only 10,800 points, and each one branches through table lookups. It actually ran slower on the GPU.

But on the CPU it costs about 28 milliseconds, and the GPU would just sit there waiting. *(point to part a)*

Here's the trick. Those forces only need velocities from the start of the step, and nobody uses them until much later. So we split the turbine model in two. *(point to part b)* The GPU samples the velocities and moves on to convection, while the CPU computes forces in parallel. Then the forces go back to the GPU.

That saves 30 milliseconds per step, and the GPU is now busy 93 percent of the time.

## 15. Setup and Correctness

Quick note on setup. Everything runs on Perlmutter at NERSC, with four A100s per node. For the CPU baseline, we always compare to the fastest CPU setup we could find.

Before we talk speed, we checked correctness. *(point to the figure)* We ran one turbine on both versions from the same start. After 1,000 steps, the difference is around 10 to the minus 13. That's floating point roundoff. The two versions agree.

## 16. Each Optimization Stacks: 40× on 16 GPUs

So, how fast is it? This is the production case: four CPU nodes against four GPU nodes.

*(walk down the bars)* Explicit residency alone gets 4.9 times. Moving the turbines to the GPU takes us to 11. Pipelining gets 21, batching 34, and overlap brings it to 40 times. Each step fixes a different bottleneck, so the gains stack up.

A step goes from 6.5 seconds down to 0.16 seconds. The GPU is busy 93 percent of the time, and only a couple of megabytes cross PCIe per step.

## 17. Strong Scaling to 128 GPUs

Now scaling. *(point to the left plot)* On the production grid, 64 GPUs bring a step down to 72 milliseconds. That's 90 times faster than the best CPU run. Efficiency stays around 87 to 90 percent each time we double the GPUs. On the biggest grid, 1.36 billion cells, we scale to 128 GPUs and do 16 billion cell updates per second.

*(point to the right plot)* Where does the time go? The compute stages shrink nicely. What's left at high GPU counts is this flat pink part, about 33 to 36 milliseconds. That's small collectives and kernel launches, so it's latency, not slow kernels.

## 18. Weak Scaling and Kernel Efficiency

For weak scaling, we keep the work per GPU fixed. At our production load, we hold 90 percent efficiency from 4 to 64 GPUs.

*(point to the roofline)* And the kernels themselves are in good shape. Our own kernels hit 67 to 88 percent of peak memory bandwidth, and the cuFFT kernels hit 48 to 82 percent. So there isn't much left to squeeze out of them.

## 19. Takeaways

Let me wrap up.

This is the first GPU port of LESGO: about 70 thousand lines of Fortran, the full physics, and still one source tree.

The big lesson: for codes like this, data movement sets the speed, not the kernels. A small set of treatments covered every coupling point we found.

On top of that, three optimizations, pipelining, batching, and overlap, push GPU utilization to 93 percent.

In the end, we're 40 to 90 times faster than the best CPU runs. A production campaign that took months now takes days.

## 20. Thank You

Thanks for listening. I'm happy to take questions.
