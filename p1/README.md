# DRAFT!  Don't start yet.

# P1 (mini project): Predicting COVID Deaths with PyTorch

## Overview

In this project, we'll use PyTorch to create a regression model that
can predict how many deaths there will be for a WI census tract, given
the number of people who have tested positive, broken down by age.  We
provide CSV files based on this dataset: https://data.dhsgis.wi.gov/datasets/wi-dhs::covid-19-vaccination-data-by-census-tract

Learning objectives:
* multiply tensors
* use GPUs (when available)
* optimize inputs to minimize outputs
* use optimization to optimize regression coefficients

Before starting, please review the [general project directions](../projects.md).

## Part 1: Prediction with Hardcoded Model

Install some packages:

```
pip3 install pandas torch
```

If your process gets killed when installing torch, try the following command instead:
```
pip3 install -f https://download.pytorch.org/whl/torch_stable.html torch==1.13.1+cpu
```

Use train.csv and test.csv to construct four PyTorch tensors:
`trainX`, `trainY`, `testX`, and `testY`.  Hints:

* you can use `pd.read_csv` to load CSVs to DataFrames
* you can use use `df.values` to get a numpy array from a DataFrame
* you can convert from numpy to PyTorch (https://pytorch.org/tutorials/beginner/basics/tensorqs_tutorial.html)
* you'll need to do some 2D slicing: the last column contains your y values and the others contain your X values

`trainX` (number of positive COVID tests per tract, by age group) should look like this:

```python
tensor([[ 23,  51,  42,  ...,  58,  26,   0],
        [ 21,  31, 210,  ...,   9,   0,   0],
        [ 82, 124, 236,  ...,  71,  21,   8],
        ...,
        [266, 355, 273,  ..., 103,  43,   6],
        [ 81, 115,  89,  ...,  35,   9,   0],
        [114, 155, 189,  ...,  19,   0,   0]])
```

`trainY` (number of COVID deaths per tract) should look like this:

```python
tensor([[3],
        [2],
        [9],
        ...,
        [5],
        [2],
        [5]])
```

Let's predict the number of COVID deaths in the test dataset under the
assumption that the deathrate is 0.004 for those <60 and 0.03 for those >=60.
Encode these assumptions as coefficients in a tensor by pasting
the following:

```python
coef = torch.tensor([
        [0.0040],
        [0.0040],
        [0.0040],
        [0.0040],
        [0.0040],
        [0.0040], # POS_50_59_CP
        [0.0300], # POS_60_69_CP
        [0.0300],
        [0.0300],
        [0.0300]
], dtype=testX.dtype)
coef
```

Multiply the first row `testX` by the `coef` vector and use `.item()`
to print the predicted number of deaths in this tract.

Requirement: your code should be written such that if
`torch.cuda.is_available()` is true, all your tensors (`trainX`,
`trainY`, `testX`, `testY`, and `coef`) should be move to a GPU prior
to any multiplication.

## Part 2: R^2 Score

Create a `predictedY` tensor by multiplying all of `testX` by `coef`.
We'll measure the quality of these predictions by writing a function
that can compare `predictedY` to the true values in `testY`.

The R^2 score
(https://en.wikipedia.org/wiki/Coefficient_of_determination) can be
used as a measure of how much variance is a y column a model can
predict (with 1 being the best score).  Different definitions are
sometimes used, but we'll define it in terms of two variables:

* **SStot**.  To compute this, first compute the average testY value.  Subtract to get the difference between each testY value and the average.  Square the differences, then add the results to get `SStot`
* **SSreg**.  Same as SStot, but instead of subtracting the average from each testY value, subtract the prediction from `testY`

If our predictions are good, `SSreg` will be much smaller than `SStot`.  So define `improvement = SStot - SSreg`.

The R^2 score is just `improvement/SStot`.

Generalize the above logic into an `r2_score(trueY, predictedY)` that
you write that can compute the R^2 score given any vector of true
values alongside a vector of predictions.

Call `r2_score(testY, predictedY)` and display the value in your notebook.

## Part 3: Optimization

Let's say `y = x^2 - 8x + 19`.  We want to find the x value that minimizes y.

First, what is y when x is a tensor containing 0.0?

```python
x = torch.tensor(0.0)
y = x**2 - 8*x + 19
y
```

We can use a PyTorch optimizer to try to find a good x value.  The
optimizer will run a loop where it computes y, computes how a small
change in x would effect y, then makes a small change to x to try to
make y smaller.

There are many optimizers in PyTorch; we'll use SGD here.  You can
create the optimizer like this:

```python
optimizer = torch.optim.SGD([????], lr=0.1)
```

For `????`, you can pass in one or more tensors that you're trying to
optimize (in this case, you're trying to find the best value for `x`).

The optimizer is based on gradients (an idea from Calculus, but you
don't need to know Calculus to do this project).  You'll need to pass
`requires_grad=True` to `torch.tensor` in your earlier code that
defined `x` so that we can track gradients.

Write a loop that executes the following 30 times:

```python
    optimizer.zero_grad()
    y = ????
    y.backward()
    optimizer.step()
    print(x, y)
```

Notice the small changes to x with each iteration (and resulting
changes to y).  Report `x.item()` in your notebook as the optimized
value.

Create a line plot of x and y values to verify that best x value you
found via optimization seems about right.

## Part 4: Linear Regression

In part 1, you used a hardcoded `coef` vector to predict COVID deaths.  Now, you will start with random coefficients and optimize them.

Steps:
* create a TensorDataset (https://pytorch.org/docs/stable/data.html#torch.utils.data.TensorDataset) from your trainX and trainY.
* create a DataLoader (https://pytorch.org/docs/stable/data.html#torch.utils.data.DataLoader) that uses your dataset
  * use shuffle
  * try different batch sizes
* create a simple linear model by initializing `torch.nn.Linear`
  * choose the size based on trainX and trainY
* create an optimizer from `torch.optim.SGD` that will optimize the `.weight` and `.bias` parameters of your model
* Optional: Feel free to use another optimizer or learning rate schedule 
  * try different learning rates
* write a training loop to optimize your model with data from your DataLoader
  * try different numbers of epochs
  * calculate your loss with `torch.nn.MSELoss`

Requirements:
* report the `r2_score` of your predictions on the test data; you must get >0.5
* print out how long training took to run
* create a bar plot showing each of the numbers in your `model.weight` tensor.  The x-axis should indicate the column names corresponding to each coefficient (from train.columns)

Optional:
* To help debug your program, feel free to install Tensorboard:
```
pip3 install tensorboard
```
* This tutorial (https://pytorch.org/tutorials/intermediate/tensorboard_tutorial.html) illustrates how you may use tensorboard to monitor training.

## Submission

You should submit your notebook as a `p1.ipynb`.

## Approximate Rubric:

The following is approximately how we will grade, but we may make
changes if we overlooked an important part of the specification or did
not consider a common mistake.

1. [x/1] prediction from hardcoded coefficient vector (part 1)
2. [x/1] when available, the tensors being multiplied are moved to a GPU (part 1)
3. [x/1] the R^2 score is computed correctly (part 2)
4. [x/1] the R^2 score is computed via a reusable function (part 2)
5. [x/1] the best x value is found (part 3)
6. [x/1] the line plot is correct (part 3)
7. [x/1] the training loop correctly optimizes the coefficients (part 4)
8. [x/1] the R^2 score is reported and >0.5 (part 4)
9. [x/1] the execution time is printed (part 4)
10. [x/1] a bar plot shows the coefficients (part 4)
