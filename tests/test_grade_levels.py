"""Tests for grade-level code handling.

The OSPI assessment datasets store `gradelevel` as zero-padded codes ("03"),
not display labels ("3rd Grade"). Querying with a label matches zero rows, so
these tests pin the constant to the vocabulary the API actually uses.
"""

import pytest

from config.settings import get_settings

# The literal values returned by SELECT DISTINCT gradelevel on both
# x73g-mrqp (2023-24) and h5d9-vgwi (2024-25).
API_GRADE_VALUES = {"03", "04", "05", "06", "07", "08", "10", "11", "All Grades"}


@pytest.fixture
def settings():
    return get_settings()


class TestGradeLevelConstants:
    def test_all_options_are_valid_api_values(self, settings):
        assert set(settings.GRADE_LEVELS) <= API_GRADE_VALUES

    def test_no_display_labels_leak_into_query_values(self, settings):
        assert not any("Grade" in g for g in settings.GRADE_LEVELS if g != "All Grades")

    def test_all_grades_is_first(self, settings):
        assert settings.GRADE_LEVELS[0] == "All Grades"

    def test_every_option_has_a_label(self, settings):
        assert all(g in settings.GRADE_LABELS for g in settings.GRADE_LEVELS)

    def test_numeric_order_is_preserved(self, settings):
        codes = settings.GRADE_LEVELS[1:]
        assert codes == sorted(codes, key=int)


class TestGradeLabel:
    def test_code_to_label(self, settings):
        assert settings.grade_label("03") == "3rd Grade"
        assert settings.grade_label("10") == "10th Grade"

    def test_all_grades_passes_through(self, settings):
        assert settings.grade_label("All Grades") == "All Grades"

    def test_unknown_code_passes_through(self, settings):
        assert settings.grade_label("99") == "99"


class TestGradeCode:
    def test_label_to_code(self, settings):
        assert settings.grade_code("3rd Grade") == "03"
        assert settings.grade_code("11th Grade") == "11"

    def test_code_passes_through(self, settings):
        assert settings.grade_code("03") == "03"

    def test_all_grades_passes_through(self, settings):
        assert settings.grade_code("All Grades") == "All Grades"

    def test_unknown_passes_through(self, settings):
        assert settings.grade_code("Kindergarten") == "Kindergarten"

    def test_roundtrip(self, settings):
        for code in settings.GRADE_LEVELS:
            assert settings.grade_code(settings.grade_label(code)) == code


# The literal `studentgroup` values in the 2024-25 dataset (h5d9-vgwi),
# excluding the "Non-*" complement groups the app does not offer.
API_STUDENT_GROUPS_2024_25 = {
    "All Students", "American Indian/ Alaskan Native", "Asian",
    "Black/ African American", "English Language Learners", "Female",
    "Foster Care", "Gender X", "Hispanic/ Latino of any race(s)", "Homeless",
    "Low-Income", "Male", "Migrant", "Military Parent",
    "Native Hawaiian/Pacific Islander", "Section 504",
    "Students with Disabilities", "Students without Disabilities",
    "Two Or More Races", "White",
}


class TestStudentGroupConstants:
    def test_all_options_are_valid_api_values(self, settings):
        offered = set(settings.STUDENT_GROUPS_CORE + settings.STUDENT_GROUPS_EXTENDED)
        assert offered <= API_STUDENT_GROUPS_2024_25

    def test_all_students_is_first(self, settings):
        assert settings.STUDENT_GROUPS_CORE[0] == "All Students"

    def test_core_and_extended_do_not_overlap(self, settings):
        assert not set(settings.STUDENT_GROUPS_CORE) & set(settings.STUDENT_GROUPS_EXTENDED)


class TestStudentGroupLabel:
    def test_irregular_spacing_is_tidied_for_display(self, settings):
        assert settings.student_group_label("Black/ African American") == "Black/African American"
        assert settings.student_group_label("Two Or More Races") == "Two or More Races"

    def test_unmapped_group_passes_through(self, settings):
        assert settings.student_group_label("Low-Income") == "Low-Income"


class TestStudentGroupForYear:
    def test_two_or_more_races_uses_old_spelling_before_2023_24(self, settings):
        assert settings.student_group_for_year("Two Or More Races", "2021-22") == "TwoorMoreRaces"
        assert settings.student_group_for_year("Two Or More Races", "2022-23") == "TwoorMoreRaces"

    def test_two_or_more_races_keeps_current_spelling_after(self, settings):
        assert settings.student_group_for_year("Two Or More Races", "2023-24") == "Two Or More Races"
        assert settings.student_group_for_year("Two Or More Races", "2024-25") == "Two Or More Races"

    def test_native_hawaiian_uses_old_spelling_through_2023_24(self, settings):
        assert (settings.student_group_for_year("Native Hawaiian/Pacific Islander", "2023-24")
                == "Native Hawaiian/ Other Pacific Islander")

    def test_native_hawaiian_keeps_current_spelling_in_2024_25(self, settings):
        assert (settings.student_group_for_year("Native Hawaiian/Pacific Islander", "2024-25")
                == "Native Hawaiian/Pacific Islander")

    def test_unaliased_group_is_unchanged(self, settings):
        assert settings.student_group_for_year("Low-Income", "2021-22") == "Low-Income"
