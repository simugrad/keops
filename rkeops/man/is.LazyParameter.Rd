% Generated by roxygen2: do not edit by hand
% Please edit documentation in R/lazytensor_preprocess.R
\name{is.LazyParameter}
\alias{is.LazyParameter}
\title{is.LazyParameter?}
\usage{
is.LazyParameter(x)
}
\arguments{
\item{x}{A \code{LazyTensor} object that we want to know if it is a
\code{LazyParameter}.}
}
\value{
A boolean, TRUE or FALSE.
}
\description{
Checks whether if the given input is a \code{LazyTensor} encoding
a single scalar value. That is, if the input is a fixed parameter
\code{LazyTensor} of dimension 1.
}
\details{
If \code{x} is a fixed scalar parameter \code{LazyTensor},
\code{is.LazyParameter(x)} returns TRUE, else, returns FALSE.
}
\examples{
\dontrun{
# basic example
scal <- 3.14
cplx <- 2 + 3i
v <- rep(3, 10)
x <- matrix(runif(100 * 3), 100, 3)

# create LazyTensor and ComplexLazyTensor
scal_LT <- LazyTensor(scal)
cplx_LT <- LazyTensor(cplx)
v_LT <- LazyTensor(v)
x_i <- LazyTensor(x, index = 'i')

# call is.LazyParameter
is.LazyParameter(scal_LT) # returns TRUE
is.LazyParameter(cplx_LT) # returns FALSE
is.LazyParameter(v_LT) # returns FALSE
is.LazyParameter(x_i) # returns FALSE
}
}
\author{
Chloe Serre-Combe, Amelie Vernay
}
