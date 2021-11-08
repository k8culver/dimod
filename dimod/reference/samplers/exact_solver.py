# Copyright 2018 D-Wave Systems Inc.
#
#    Licensed under the Apache License, Version 2.0 (the "License");
#    you may not use this file except in compliance with the License.
#    You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.

"""
Solvers that calculate the energy of all possible samples.

Note:
    These samplers are designed for use in testing. Because they calculate
    energy for every possible sample, they are very slow.
"""
from itertools import product
from typing import TYPE_CHECKING

import numpy as np

from dimod.core.sampler import Sampler
from dimod.sampleset import SampleSet
from dimod.core.polysampler import PolySampler
from dimod.vartypes import Vartype
if TYPE_CHECKING:
    from dimod import BinaryQuadraticModel, BinaryPolynomial, DiscreteQuadraticModel, ConstrainedQuadraticModel

__all__ = ['ExactSolver', 'ExactPolySolver', 'ExactDQMSolver', 'ExactCQMSolver']


class ExactSolver(Sampler):
    """A simple exact solver for testing and debugging code using your local CPU.

    Notes:
        This solver becomes slow for problems with 18 or more
        variables.

    Examples:
        This example solves a two-variable Ising model.

        >>> h = {'a': -0.5, 'b': 1.0}
        >>> J = {('a', 'b'): -1.5}
        >>> sampleset = dimod.ExactSolver().sample_ising(h, J)
        >>> print(sampleset)   # doctest: +SKIP
           a  b energy num_oc.
        0 -1 -1   -2.0       1
        2 +1 +1   -1.0       1
        1 +1 -1    0.0       1
        3 -1 +1    3.0       1
        ['SPIN', 4 rows, 4 samples, 2 variables]

        This example solves a two-variable QUBO.

        >>> Q = {('a', 'b'): 2.0, ('a', 'a'): 1.0, ('b', 'b'): -0.5}
        >>> sampleset = dimod.ExactSolver().sample_qubo(Q)
        >>> sampleset.first.sample
        {'a': 0, 'b': 1}

        This example solves a two-variable binary quadratic model.

        >>> bqm = dimod.BinaryQuadraticModel({'a': 1.5}, {('a', 'b'): -1}, 0.0, 'SPIN')
        >>> sampleset = dimod.ExactSolver().sample(bqm)
        >>> sampleset.first.energy
        -2.5

    """
    properties = None
    parameters = None

    def __init__(self):
        self.properties = {}
        self.parameters = {}

    def sample(self, bqm: 'BinaryQuadraticModel', **kwargs) -> SampleSet:
        """Sample from a binary quadratic model.

        Args:
            bqm (:class:`~dimod.BinaryQuadraticModel`):
                Binary quadratic model to be sampled from.

        Returns:
            :class:`~dimod.SampleSet`

        """
        kwargs = self.remove_unknown_kwargs(**kwargs)

        if not len(bqm.variables):
            return SampleSet.from_samples([], bqm.vartype, energy=[])

        samples = _graycode(bqm)

        if bqm.vartype is Vartype.SPIN:
            samples = 2*samples - 1

        return SampleSet.from_samples_bqm((samples, list(bqm.variables)), bqm)


class ExactPolySolver(PolySampler):
    """A simple exact polynomial solver for testing/debugging code on your CPU.

    Notes:
        This solver becomes slow for problems with 18 or more
        variables.

    Examples:
        This example solves a three-variable hising model.

        >>> h = {'a': -0.5, 'b': 1.0, 'c': 0.}
        >>> J = {('a', 'b'): -1.5, ('a', 'b', 'c'): -1.0}
        >>> sampleset = dimod.ExactPolySolver().sample_hising(h, J)
        >>> print(sampleset)      # doctest: +SKIP
           a  b  c energy num_oc.
        1 -1 -1 +1   -3.0       1
        5 +1 +1 +1   -2.0       1
        0 -1 -1 -1   -1.0       1
        3 +1 -1 -1   -1.0       1
        4 +1 +1 -1    0.0       1
        2 +1 -1 +1    1.0       1
        7 -1 +1 -1    2.0       1
        6 -1 +1 +1    4.0       1
        ['SPIN', 8 rows, 8 samples, 3 variables]

        This example solves a three-variable HUBO.

        >>> Q = {('a', 'b'): 2.0, ('c',): 1.0, ('a', 'b', 'c'): -0.5}
        >>> sampleset = dimod.ExactPolySolver().sample_hubo(Q)
        >>> sampleset.first.energy
        0.0

        This example solves a three-variable binary polynomial

        >>> poly = dimod.BinaryPolynomial({('a',): 1.5, ('a', 'b'): -1, ('a', 'b', 'c'): 0.5}, 'SPIN')
        >>> sampleset = dimod.ExactPolySolver().sample_poly(poly)
        >>> sampleset.first.sample
        {'a': -1, 'b': -1, 'c': -1}

    """
    properties = None
    parameters = None

    def __init__(self):
        self.properties = {}
        self.parameters = {}

    def sample_poly(self, polynomial: 'BinaryPolynomial', **kwargs) -> SampleSet:
        """Sample from a binary polynomial.

        Args:
            polynomial (:class:`~dimod.BinaryPolynomial`):
                Binary polynomial to be sampled from.

        Returns:
            :class:`~dimod.SampleSet`

        """
        return ExactSolver().sample(polynomial, **kwargs)


class ExactDQMSolver():
    """A simple exact solver for testing and debugging code using your local CPU.

    Notes:
        This solver calculates the energy for every possible
        combination of variable cases. If variable i has
        k_i many cases, this will be k_1 * k_2 * ... * k_n
        which grows exponentially for constant k_i in the
        number of variables.

    """

    def __init__(self):
        self.properties = {}
        self.parameters = {}

    def sample_dqm(self, dqm: 'DiscreteQuadraticModel', **kwargs) -> SampleSet:
        """Sample from a discrete quadratic model.

        Args:
            dqm (:class:`~dimod.DiscreteQuadraticModel`):
                Discrete quadratic model to be sampled from.

        Returns:
            :class:`~dimod.SampleSet`

        """
        Sampler.remove_unknown_kwargs(self, **kwargs)
        
        if not dqm.num_variables():
            return SampleSet.from_samples([], 'DISCRETE', energy=[])

        cases = _all_cases_dqm(dqm)
        energies = dqm.energies(cases)
        
        return SampleSet.from_samples(cases, 'DISCRETE', energies)
    
    
class ExactCQMSolver():
    """A simple exact solver for testing and debugging code using your local CPU.

    Notes:
        This solver calculates the energy for every possible
        combination of variable cases. It becomes slow very quickly
        
    Examples:
        This example solves a CQM with 3 variables and 1 constraint.
        
        >>> from dimod import ConstrainedQuadraticModel, Binary
        >>> cqm = ConstrainedQuadraticModel()
        >>> x, y, z = Binary('x'), Binary('y'), Binary('z')
        >>> cqm.set_objective(x*y + 2*y*z)
        >>> cqm.add_constraint(x*y == 1, label='constraint_1')
        'constraint_1'
        >>> sampleset = dimod.ExactCQMSolver().sample_cqm(cqm)
        >>> print(sampleset)      # doctest: +SKIP
          x y z energy num_oc. is_sat. is_fea.
        0 0 0 0    0.0       1 arra...   False
        1 0 1 0    0.0       1 arra...   False
        2 1 0 0    0.0       1 arra...   False
        4 0 0 1    0.0       1 arra...   False
        6 1 0 1    0.0       1 arra...   False
        3 1 1 0    1.0       1 arra...    True
        5 0 1 1    2.0       1 arra...   False
        7 1 1 1    3.0       1 arra...    True
        ['INTEGER', 8 rows, 8 samples, 3 variables]
        
    """
    def __init__(self):
        self.properties = {}
        self.parameters = {}
        
    def sample_cqm(self, cqm: 'ConstrainedQuadraticModel', rtol: float = 1e-6, atol: float = 1e-8, **kwargs) -> SampleSet:
        """Sample from a constrained quadratic model.

        Args:
            cqm (:class:`~dimod.ConstrainedQuadraticModel`):
                Constrained quadratic model to be sampled from.
            rtol (float):
                The relative tolerance for constraint violation, scales sample energy 
            atol (float):
                The absolute tolerance for constraint violations, constant for sample energy

        Returns:
            :class:`~dimod.SampleSet`

        """
        Sampler.remove_unknown_kwargs(self, **kwargs)
        
        if not len(cqm.variables):
            return SampleSet.from_samples([], 'INTEGER', energy=[])
        
        cases = _all_cases_cqm(cqm)
        energies = cqm.objective.energies(cases)
        
        is_satisfied = [[violation <= atol + rtol*abs(energies[i]) for _, violation in cqm.iter_violations((cases[0][i],cases[1]))] for i in range(len(cases[0]))]
        is_feasible = [all(satisfied) for satisfied in is_satisfied]
        
        # from_samples requires a single vartype argument, but QuadraticModel
        # and therefore CQM allow mixed vartypes. For now, only passing 'INTEGER'
        return SampleSet.from_samples(cases, 'INTEGER', energies, is_feasible=is_feasible, is_satisfied=is_satisfied)


def _graycode(bqm):
    """Get a numpy array containing all possible samples in a gray-code order"""
    # developer note: there are better/faster ways to do this, but because
    # we're limited in performance by the energy calculation, this is probably
    # more readable and easier.
    n = len(bqm.variables)
    ns = 1 << n
    samples = np.empty((ns, n), dtype=np.int8)

    samples[0, :] = 0

    for i in range(1, ns):
        v = (i & -i).bit_length() - 1  # the least significant set bit of i
        samples[i, :] = samples[i - 1, :]
        samples[i, v] = not samples[i - 1, v]

    return samples


def _all_cases_dqm(dqm):
    """Get a numpy array containing all possible samples as lists of integers"""
    # developer note: there may be better ways to do this, but because we're
    # limited in performance by the energy calculation, this is probably fine

    cases = [range(dqm.num_cases(v)) for v in dqm.variables] 
    return np.array(np.meshgrid(*cases)).T.reshape(-1,dqm.num_variables()), list(dqm.variables)
    
    
def _all_cases_cqm(cqm):
    """Get a numpy array containing all possible samples as lists of valid values"""
    # developer note: the following is a catch all method, and it may be possible
    # to streamline or refactor. It is fine for its intended use
    
    var_list = list(cqm.variables)
    
    # Set aside logical discrete variables, and the Binary variables which make them up
    d_cases = [len(cqm.constraints[d].lhs) for d in cqm.discrete]
    d_vars = [x for l in [list(cqm.constraints[d].lhs.variables) for d in cqm.discrete] for x in l]
    s = set(d_vars)
    var_list = [v for v in var_list if v not in s]
    
    # Construct all combinations of spin, integer, and binary variables not included in discrete
    cases = [_iterator_by_vartype(cqm, v) for v in var_list]
    c1 = np.array(np.meshgrid(*cases))
    if len(var_list):
        c1 = c1.T.reshape(-1,len(var_list))
    
    # Concatenate each discrete variable cases with each non-discrete variable cases
    combinations = []
    for indexes in product(*[range(d) for d in d_cases]):
        if not len(indexes):
            break
            
        l = []
        for i in range(len(indexes)):
            s = np.zeros(d_cases[i])
            s[indexes[i]] = 1
            l = np.concatenate([l, s])
        
        if len(c1):
            for row in c1:
                combinations.append(np.concatenate([l, row]))
        else:
            combinations.append(l)
    
    var_list = d_vars + var_list
    
    # If nothing was added to combinations, then there are no discrete variables
    if not len(combinations):
        combinations = c1
    
    return np.array(combinations), var_list
    
    
def _iterator_by_vartype(cqm, v):
    if cqm.vartype(v) is Vartype.BINARY:
        return range(2)
    if cqm.vartype(v) is Vartype.SPIN:
        return [-1, 1]
    if cqm.vartype(v) is Vartype.INTEGER:
        return range(int(cqm.lower_bound(v)), int(cqm.upper_bound(v)+1))
    raise ValueError("Only Binary, Spin, or Integer variables supported by ExactCQMSolver")
