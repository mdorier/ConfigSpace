# Copyright (c) 2014-2016, ConfigSpace developers
# Matthias Feurer
# Katharina Eggensperger
# and others (see commit history).
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * Neither the name of the <organization> nor the
#       names of its contributors may be used to endorse or promote products
#       derived from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL <COPYRIGHT HOLDER> BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
from __future__ import annotations

import os
import tempfile
import warnings
from io import StringIO

import pytest

from ConfigSpace.conditions import (
    AndConjunction,
    EqualsCondition,
    GreaterThanCondition,
    InCondition,
    NotEqualsCondition,
    OrConjunction,
)
from ConfigSpace.configuration_space import ConfigurationSpace
from ConfigSpace.forbidden import (
    ForbiddenAndConjunction,
    ForbiddenEqualsClause,
    ForbiddenGreaterThanRelation,
    ForbiddenInClause,
)
from ConfigSpace.hyperparameters import (
    CategoricalHyperparameter,
    OrdinalHyperparameter,
    UniformFloatHyperparameter,
    UniformIntegerHyperparameter,
)

with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    from ConfigSpace.read_and_write import pcs, pcs_new

# More complex search space
classifier = CategoricalHyperparameter("classifier", ["svm", "nn"])
kernel = CategoricalHyperparameter("kernel", ["rbf", "poly", "sigmoid"])
kernel_condition = EqualsCondition(kernel, classifier, "svm")
C = UniformFloatHyperparameter("C", 0.03125, 32768, log=True)
C_condition = EqualsCondition(C, classifier, "svm")
gamma = UniformFloatHyperparameter("gamma", 0.000030518, 8, log=True)
gamma_condition = EqualsCondition(gamma, kernel, "rbf")
degree = UniformIntegerHyperparameter("degree", 1, 5)
degree_condition = InCondition(degree, kernel, ["poly", "sigmoid"])
neurons = UniformIntegerHyperparameter("neurons", 16, 1024)
neurons_condition = EqualsCondition(neurons, classifier, "nn")
lr = UniformFloatHyperparameter("lr", 0.0001, 1.0)
lr_condition = EqualsCondition(lr, classifier, "nn")
preprocessing = CategoricalHyperparameter("preprocessing", ["None", "pca"])
conditional_space = ConfigurationSpace()
conditional_space.add(preprocessing)
conditional_space.add(classifier)
conditional_space.add(kernel)
conditional_space.add(C)
conditional_space.add(neurons)
conditional_space.add(lr)
conditional_space.add(degree)
conditional_space.add(gamma)

conditional_space.add(C_condition)
conditional_space.add(kernel_condition)
conditional_space.add(lr_condition)
conditional_space.add(neurons_condition)
conditional_space.add(degree_condition)
conditional_space.add(gamma_condition)

float_a = UniformFloatHyperparameter("float_a", -1.23, 6.45)
e_float_a = UniformFloatHyperparameter("e_float_a", 0.5e-2, 4.5e06)
int_a = UniformIntegerHyperparameter("int_a", -1, 6)
log_a = UniformFloatHyperparameter("log_a", 4e-1, 6.45, log=True)
int_log_a = UniformIntegerHyperparameter("int_log_a", 1, 6, log=True)
cat_a = CategoricalHyperparameter("cat_a", ["a", "b", "c", "d"])
crazy = CategoricalHyperparameter(r"@.:;/\?!$%&_-<>*+1234567890", ["const"])
easy_space = ConfigurationSpace()
easy_space.add(float_a)
easy_space.add(e_float_a)
easy_space.add(int_a)
easy_space.add(log_a)
easy_space.add(int_log_a)
easy_space.add(cat_a)
easy_space.add(crazy)


def test_read_configuration_space_basic():
    # TODO: what does this test has to do with the PCS converter?
    float_a_copy = UniformFloatHyperparameter("float_a", -1.23, 6.45)
    a_copy = {"a": float_a_copy, "b": int_a}
    a_real = {"b": int_a, "a": float_a}
    assert a_real == a_copy


"""
Tests for the "older pcs" version

"""


def test_read_configuration_space_easy():
    expected = StringIO()
    expected.write("# This is a \n")
    expected.write("   # This is a comment with a leading whitespace ### ffds \n")
    expected.write("\n")
    expected.write("float_a [-1.23, 6.45] [2.61] # bla\n")
    expected.write("e_float_a [.5E-2, 4.5e+06] [2250000.0025]\n")
    expected.write("int_a [-1, 6] [2]i\n")
    expected.write("log_a [4e-1, 6.45] [1.6062378404]l\n")
    expected.write("int_log_a [1, 6] [2]il\n")
    expected.write('cat_a {a,"b",c,d} [a]\n')
    expected.write(r'@.:;/\?!$%&_-<>*+1234567890 {"const"} ["const"]\n')
    expected.seek(0)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        cs = pcs.read(expected)
    assert cs == easy_space


def test_read_configuration_space_conditional():
    # More complex search space as string array
    complex_cs = []
    complex_cs.append("preprocessing {None, pca} [None]")
    complex_cs.append("classifier {svm, nn} [svm]")
    complex_cs.append("kernel {rbf, poly, sigmoid} [rbf]")
    complex_cs.append("C [0.03125, 32768] [32]l")
    complex_cs.append("neurons [16, 1024] [520]i # Should be Q16")
    complex_cs.append("lr [0.0001, 1.0] [0.50005]")
    complex_cs.append("degree [1, 5] [3]i")
    complex_cs.append("gamma [0.000030518, 8] [0.0156251079996]l")

    complex_cs.append("C | classifier in {svm}")
    complex_cs.append("kernel | classifier in {svm}")
    complex_cs.append("lr | classifier in {nn}")
    complex_cs.append("neurons | classifier in {nn}")
    complex_cs.append("degree | kernel in {poly, sigmoid}")
    complex_cs.append("gamma | kernel in {rbf}")

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        cs = pcs.read(complex_cs)
    assert cs == conditional_space


def test_read_configuration_space_conditional_with_two_parents():
    config_space = []
    config_space.append("@1:0:restarts {F,L,D,x,+,no}[x]")
    config_space.append("@1:S:Luby:aryrestarts {1,2}[1]")
    config_space.append("@1:2:Luby:restarts [1,65535][1000]il")
    config_space.append("@1:2:Luby:restarts | @1:0:restarts in {L}")
    config_space.append("@1:2:Luby:restarts | @1:S:Luby:aryrestarts in {2}")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        cs = pcs.read(config_space)
    assert len(cs.conditions) == 1
    assert isinstance(cs.conditions[0], AndConjunction)


def test_write_illegal_argument():
    sp = {"a": int_a}
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        with pytest.raises(TypeError):
            pcs.write(sp)  # type: ignore


def test_write_int():
    expected = "int_a [-1, 6] [2]i"
    cs = ConfigurationSpace()
    cs.add(int_a)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        value = pcs.write(cs)
    assert expected == value


def test_write_log_int():
    expected = "int_log_a [1, 6] [2]il"
    cs = ConfigurationSpace()
    cs.add(int_log_a)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        value = pcs.write(cs)
    assert expected == value


def test_write_log10():
    expected = "a [10.0, 1000.0] [100.0]l"
    cs = ConfigurationSpace()
    cs.add(UniformFloatHyperparameter("a", 10, 1000, log=True))
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        value = pcs.write(cs)
    assert expected == value


def test_build_forbidden():
    expected = (
        "a {a, b, c} [a]\nb {a, b, c} [c]\n\n"
        "{a=a, b=a}\n{a=a, b=b}\n{a=b, b=a}\n{a=b, b=b}"
    )
    cs = ConfigurationSpace()
    a = CategoricalHyperparameter("a", ["a", "b", "c"], "a")
    b = CategoricalHyperparameter("b", ["a", "b", "c"], "c")
    cs.add(a)
    cs.add(b)
    fb = ForbiddenAndConjunction(
        ForbiddenInClause(a, ["a", "b"]),
        ForbiddenInClause(b, ["a", "b"]),
    )
    cs.add(fb)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        value = pcs.write(cs)
    assert expected in value


"""
Tests for the "newer pcs" version in order to check
if both deliver the same results
"""


def test_read_new_configuration_space_easy():
    expected = StringIO()
    expected.write("# This is a \n")
    expected.write("   # This is a comment with a leading whitespace ### ffds \n")
    expected.write("\n")
    expected.write("float_a real [-1.23, 6.45] [2.61] # bla\n")
    expected.write("e_float_a real [.5E-2, 4.5e+06] [2250000.0025]\n")
    expected.write("int_a integer [-1, 6] [2]\n")
    expected.write("log_a real [4e-1, 6.45] [1.6062378404]log\n")
    expected.write("int_log_a integer [1, 6] [2]log\n")
    expected.write('cat_a categorical {a,"b",c,d} [a]\n')
    expected.write(r'@.:;/\?!$%&_-<>*+1234567890 categorical {"const"} ["const"]\n')
    expected.seek(0)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        cs = pcs_new.read(expected)
    assert cs == easy_space


def test_read_new_configuration_space_conditional():
    # More complex search space as string array
    complex_cs = []
    complex_cs.append("preprocessing categorical {None, pca} [None]")
    complex_cs.append("classifier categorical {svm, nn} [svm]")
    complex_cs.append("kernel categorical {rbf, poly, sigmoid} [rbf]")
    complex_cs.append("C real [0.03125, 32768] [32]log")
    complex_cs.append("neurons integer [16, 1024] [520] # Should be Q16")
    complex_cs.append("lr real [0.0001, 1.0] [0.50005]")
    complex_cs.append("degree integer [1, 5] [3]")
    complex_cs.append("gamma real [0.000030518, 8] [0.0156251079996]log")

    complex_cs.append("C | classifier in {svm}")
    complex_cs.append("kernel | classifier in {svm}")
    complex_cs.append("lr | classifier in {nn}")
    complex_cs.append("neurons | classifier in {nn}")
    complex_cs.append("degree | kernel in {poly, sigmoid}")
    complex_cs.append("gamma | kernel in {rbf}")

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        cs_new = pcs_new.read(complex_cs)
    assert cs_new == conditional_space

    # same in older version
    complex_cs_old = []
    complex_cs_old.append("preprocessing {None, pca} [None]")
    complex_cs_old.append("classifier {svm, nn} [svm]")
    complex_cs_old.append("kernel {rbf, poly, sigmoid} [rbf]")
    complex_cs_old.append("C [0.03125, 32768] [32]l")
    complex_cs_old.append("neurons [16, 1024] [520]i # Should be Q16")
    complex_cs_old.append("lr [0.0001, 1.0] [0.50005]")
    complex_cs_old.append("degree [1, 5] [3]i")
    complex_cs_old.append("gamma [0.000030518, 8] [0.0156251079996]l")

    complex_cs_old.append("C | classifier in {svm}")
    complex_cs_old.append("kernel | classifier in {svm}")
    complex_cs_old.append("lr | classifier in {nn}")
    complex_cs_old.append("neurons | classifier in {nn}")
    complex_cs_old.append("degree | kernel in {poly, sigmoid}")
    complex_cs_old.append("gamma | kernel in {rbf}")

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        cs_old = pcs.read(complex_cs_old)

    assert cs_old == cs_new


def test_write_new_illegal_argument():
    sp = {"a": int_a}
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        with pytest.raises(TypeError):
            pcs_new.write(sp)  # type: ignore


def test_write_new_int():
    expected = "int_a integer [-1, 6] [2]"
    cs = ConfigurationSpace()
    cs.add(int_a)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        value = pcs_new.write(cs)
    assert expected == value


def test_write_new_log_int():
    expected = "int_log_a integer [1, 6] [2]log"
    cs = ConfigurationSpace()
    cs.add(int_log_a)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        value = pcs_new.write(cs)
    assert expected == value


def test_write_new_log10():
    expected = "a real [10.0, 1000.0] [100.0]log"
    cs = ConfigurationSpace()
    cs.add(UniformFloatHyperparameter("a", 10, 1000, log=True))
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        value = pcs_new.write(cs)
    assert expected == value


def test_build_new_forbidden():
    expected = (
        "a categorical {a, b, c} [a]\nb categorical {a, b, c} [c]\n\n"
        "{a=a, b=a}\n{a=a, b=b}\n{a=b, b=a}\n{a=b, b=b}\n"
    )
    cs = ConfigurationSpace()
    a = CategoricalHyperparameter("a", ["a", "b", "c"], "a")
    b = CategoricalHyperparameter("b", ["a", "b", "c"], "c")
    cs.add(a)
    cs.add(b)
    fb = ForbiddenAndConjunction(
        ForbiddenInClause(a, ["a", "b"]),
        ForbiddenInClause(b, ["a", "b"]),
    )
    cs.add(fb)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        value = pcs_new.write(cs)
    assert expected == value


def test_build_new_GreaterThanFloatCondition():
    expected = "b integer [0, 10] [5]\n" "a real [0.0, 1.0] [0.5]\n\n" "a | b > 5"
    cs = ConfigurationSpace()
    a = UniformFloatHyperparameter("a", 0, 1, 0.5)
    b = UniformIntegerHyperparameter("b", 0, 10, 5)
    cs.add(a)
    cs.add(b)
    cond = GreaterThanCondition(a, b, 5)
    cs.add(cond)

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        value = pcs_new.write(cs)
    assert expected == value

    expected = "b real [0.0, 10.0] [5.0]\n" "a real [0.0, 1.0] [0.5]\n\n" "a | b > 5"
    cs = ConfigurationSpace()
    a = UniformFloatHyperparameter("a", 0, 1, 0.5)
    b = UniformFloatHyperparameter("b", 0, 10, 5)
    cs.add(a)
    cs.add(b)
    cond = GreaterThanCondition(a, b, 5)
    cs.add(cond)

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        value = pcs_new.write(cs)
    assert expected == value


def test_build_new_GreaterThanIntCondition():
    expected = "a real [0.0, 1.0] [0.5]\n" "b integer [0, 10] [5]\n\n" "b | a > 0.5"
    cs = ConfigurationSpace()
    a = UniformFloatHyperparameter("a", 0, 1, 0.5)
    b = UniformIntegerHyperparameter("b", 0, 10, 5)
    cs.add(a)
    cs.add(b)
    cond = GreaterThanCondition(b, a, 0.5)
    cs.add(cond)

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        value = pcs_new.write(cs)
    assert expected == value

    expected = "a integer [0, 10] [5]\n" "b integer [0, 10] [5]\n\n" "b | a > 5"
    cs = ConfigurationSpace()
    a = UniformIntegerHyperparameter("a", 0, 10, 5)
    b = UniformIntegerHyperparameter("b", 0, 10, 5)
    cs.add(a)
    cs.add(b)
    cond = GreaterThanCondition(b, a, 5)
    cs.add(cond)

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        value = pcs_new.write(cs)
    assert expected == value


def test_read_new_configuration_space_forbidden():
    cs_with_forbidden = ConfigurationSpace()
    int_hp = UniformIntegerHyperparameter("int_hp", 0, 50, 30)
    float_hp = UniformFloatHyperparameter("float_hp", 0.0, 50.0, 30.0)
    cat_hp_str = CategoricalHyperparameter("cat_hp_str", ["a", "b", "c"], "b")
    ord_hp_str = OrdinalHyperparameter("ord_hp_str", ["a", "b", "c"], "b")

    cs_with_forbidden.add([int_hp, float_hp, cat_hp_str, ord_hp_str])

    int_hp_forbidden = ForbiddenAndConjunction(ForbiddenEqualsClause(int_hp, 1))

    float_hp_forbidden_1 = ForbiddenEqualsClause(float_hp, 1.0)
    float_hp_forbidden_2 = ForbiddenEqualsClause(float_hp, 2.0)
    float_hp_forbidden = ForbiddenAndConjunction(
        float_hp_forbidden_1,
        float_hp_forbidden_2,
    )

    cat_hp_str_forbidden = ForbiddenAndConjunction(
        ForbiddenEqualsClause(cat_hp_str, "a"),
    )
    ord_hp_float_forbidden = ForbiddenAndConjunction(
        ForbiddenEqualsClause(ord_hp_str, "a"),
    )
    cs_with_forbidden.add(
        [
            int_hp_forbidden,
            float_hp_forbidden,
            cat_hp_str_forbidden,
            ord_hp_float_forbidden,
        ],
    )

    complex_cs = []
    complex_cs.append("int_hp integer [0,50] [30]")
    complex_cs.append("float_hp real [0.0, 50.0] [30.0]")
    complex_cs.append("cat_hp_str categorical {a, b, c} [b]")
    complex_cs.append("ord_hp_str ordinal {a, b, c} [b]")
    complex_cs.append("# Forbiddens:")
    complex_cs.append("{int_hp=1}")
    complex_cs.append("{float_hp=1.0, float_hp=2.0}")
    complex_cs.append("{cat_hp_str=a}")
    complex_cs.append("{ord_hp_str=a}")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        cs_new = pcs_new.read(complex_cs)

    assert cs_new == cs_with_forbidden


def test_write_new_configuration_space_forbidden_relation():
    cs_with_forbidden = ConfigurationSpace()
    int_hp = UniformIntegerHyperparameter("int_hp", 0, 50, 30)
    float_hp = UniformFloatHyperparameter("float_hp", 0.0, 50.0, 30.0)

    forbidden = ForbiddenGreaterThanRelation(int_hp, float_hp)
    cs_with_forbidden.add([int_hp, float_hp])
    cs_with_forbidden.add(forbidden)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        with pytest.raises(TypeError):
            pcs_new.write({"configuration_space": cs_with_forbidden})  # type: ignore


def test_read_new_configuration_space_complex_conditionals():
    classi = OrdinalHyperparameter(
        "classi",
        ["random_forest", "extra_trees", "k_nearest_neighbors", "something"],
    )
    knn_weights = CategoricalHyperparameter("knn_weights", ["uniform", "distance"])
    weather = OrdinalHyperparameter("weather", ["sunny", "rainy", "cloudy", "snowing"])
    temperature = CategoricalHyperparameter("temperature", ["high", "low"])
    rain = CategoricalHyperparameter("rain", ["yes", "no"])
    gloves = OrdinalHyperparameter("gloves", ["none", "yarn", "leather", "gortex"])
    heur1 = CategoricalHyperparameter("heur1", ["off", "on"])
    heur2 = CategoricalHyperparameter("heur2", ["off", "on"])
    heur_order = CategoricalHyperparameter("heur_order", ["heur1then2", "heur2then1"])
    gloves_condition = OrConjunction(
        EqualsCondition(gloves, rain, "yes"),
        EqualsCondition(gloves, temperature, "low"),
    )
    heur_condition = AndConjunction(
        EqualsCondition(heur_order, heur1, "on"),
        EqualsCondition(heur_order, heur2, "on"),
    )
    and_conjunction = AndConjunction(
        NotEqualsCondition(knn_weights, classi, "extra_trees"),
        EqualsCondition(knn_weights, classi, "random_forest"),
    )
    Cl_condition = OrConjunction(
        EqualsCondition(knn_weights, classi, "k_nearest_neighbors"),
        and_conjunction,
        EqualsCondition(knn_weights, classi, "something"),
    )

    and1 = AndConjunction(
        EqualsCondition(temperature, weather, "rainy"),
        EqualsCondition(temperature, weather, "cloudy"),
    )
    and2 = AndConjunction(
        EqualsCondition(temperature, weather, "sunny"),
        NotEqualsCondition(temperature, weather, "snowing"),
    )
    another_condition = OrConjunction(and1, and2)

    complex_conditional_space = ConfigurationSpace()
    complex_conditional_space.add(classi)
    complex_conditional_space.add(knn_weights)
    complex_conditional_space.add(weather)
    complex_conditional_space.add(temperature)
    complex_conditional_space.add(rain)
    complex_conditional_space.add(gloves)
    complex_conditional_space.add(heur1)
    complex_conditional_space.add(heur2)
    complex_conditional_space.add(heur_order)

    complex_conditional_space.add(gloves_condition)
    complex_conditional_space.add(heur_condition)
    complex_conditional_space.add(Cl_condition)
    complex_conditional_space.add(another_condition)

    complex_cs = []
    complex_cs.append(
        "classi ordinal {random_forest,extra_trees,k_nearest_neighbors, something} "
        "[random_forest]",
    )
    complex_cs.append("knn_weights categorical {uniform, distance} [uniform]")
    complex_cs.append("weather ordinal {sunny, rainy, cloudy, snowing} [sunny]")
    complex_cs.append("temperature categorical {high, low} [high]")
    complex_cs.append("rain categorical { yes, no } [yes]")
    complex_cs.append("gloves ordinal { none, yarn, leather, gortex } [none]")
    complex_cs.append("heur1 categorical { off, on } [off]")
    complex_cs.append("heur2 categorical { off, on } [off]")
    complex_cs.append("heur_order categorical { heur1then2, heur2then1 } [heur1then2]")
    complex_cs.append("gloves | rain == yes || temperature == low")
    complex_cs.append("heur_order | heur1 == on && heur2 == on")
    complex_cs.append(
        "knn_weights | classi == k_nearest_neighbors || "
        "classi != extra_trees && classi == random_forest || classi == something",
    )
    complex_cs.append(
        "temperature | weather == rainy && weather == cloudy || "
        "weather == sunny && weather != snowing",
    )
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        cs_new = pcs_new.read(complex_cs)
    assert cs_new == complex_conditional_space


def test_convert_restrictions():
    # This is a smoke test to make sure that the int/float values in the
    # greater or smaller statements are converted to the right type when
    # reading them
    s = """x1 real [0,1] [0]
    x2 real [0,1] [0]
    x3 real [0,1] [0]
    x4 integer [0,2] [0]
    x5 real [0,1] [0]
    x6 ordinal {cold, luke-warm, hot} [cold]
    x1 | x2 > 0.5
    x3 | x4 > 1 && x4 == 2 && x4 in {2}
    x5 | x6 > luke-warm"""

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        pcs_new.read(s.split("\n"))


def test_write_restrictions():
    s = (
        "c integer [0, 2] [0]\n"
        + "d ordinal {cold, luke-warm, hot} [cold]\n"
        + "e real [0.0, 1.0] [0.0]\n"
        + "b real [0.0, 1.0] [0.0]\n"
        + "a real [0.0, 1.0] [0.0]\n"
        + "\n"
        + "b | d in {luke-warm, hot} || c > 1\n"
        + "a | b == 0.5 && e > 0.5"
    )

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        a = pcs_new.read(s.split("\n"))
        out = pcs_new.write(a)

    assert out == s


def test_read_write():
    # Some smoke tests whether reading, writing, reading alters makes the
    #  configspace incomparable
    this_file = os.path.abspath(__file__)
    this_directory = os.path.dirname(this_file)
    configuration_space_path = os.path.join(this_directory, "..", "test_searchspaces")
    configuration_space_path = os.path.abspath(configuration_space_path)
    configuration_space_path = os.path.join(
        configuration_space_path,
        "spear-params-mixed.pcs",
    )
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        with open(configuration_space_path) as fh:
            cs = pcs.read(fh)

    tf = tempfile.NamedTemporaryFile()
    name = tf.name
    tf.close()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        with open(name, "w") as fh:
            pcs_string = pcs.write(cs)
            fh.write(pcs_string)
        with open(name) as fh:
            pcs_new = pcs.read(fh)

    assert pcs_new == cs, (pcs_new, cs)


def test_write_categorical_with_weights():
    cat = CategoricalHyperparameter("a", ["a", "b"], weights=[0.3, 0.7])
    cs = ConfigurationSpace()
    cs.add(cat)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        with pytest.raises(ValueError, match="The pcs format does not support"):
            pcs.write(cs)


def test_write_numerical_cond_and_forb():
    cs = ConfigurationSpace(seed=12345)

    hc1 = CategoricalHyperparameter(
        name="hc1",
        choices=[True, False],
        default_value=True,
    )
    hc2 = CategoricalHyperparameter(
        name="hc2",
        choices=[True, False],
        default_value=True,
    )

    hf1 = UniformFloatHyperparameter(
        name="hf1",
        lower=1.0,
        upper=10.0,
        default_value=5.0,
    )
    hi1 = UniformIntegerHyperparameter(name="hi1", lower=1, upper=10, default_value=5)
    cs.add([hc1, hc2, hf1, hi1])
    c1 = InCondition(child=hc1, parent=hc2, values=[True])
    c2 = InCondition(child=hc2, parent=hi1, values=[1, 2, 3, 4])
    c3 = GreaterThanCondition(hi1, hf1, 6.0)
    c4 = EqualsCondition(hi1, hf1, 8.0)
    c5 = AndConjunction(c3, c4)

    cs.add([c1, c2, c5])

    f1 = ForbiddenEqualsClause(hc1, False)
    f2 = ForbiddenEqualsClause(hf1, 2.0)
    f3 = ForbiddenEqualsClause(hi1, 3)
    cs.add([ForbiddenAndConjunction(f2, f3), f1])
    expected = (
        "hf1 real [1.0, 10.0] [5.0]\n"
        + "hi1 integer [1, 10] [5]\n"
        + "hc2 categorical {True, False} [True]\n"
        + "hc1 categorical {True, False} [True]\n"
        + "\n"
        + "hi1 | hf1 > 6.0 && hf1 == 8.0\n"
        + "hc2 | hi1 in {1, 2, 3, 4}\n"
        + "hc1 | hc2 in {True}\n"
        + "\n"
        + "{hc1=False}\n"
        + "{hf1=2.0, hi1=3}\n"
    )
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        out = pcs_new.write(cs)
    assert out == expected
