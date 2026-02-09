#!/usr/bin/env python3
"""
Test script for the write capability detection hook.

This creates temporary test scenarios to verify the hook works correctly.
"""

import tempfile
import shutil
from pathlib import Path
import subprocess
import sys


def create_test_scenario(scenario_name: str, code: str, has_test: bool = False):
    """Create a test scenario and run the hook."""
    print(f"\n{'='*80}")
    print(f"Test Scenario: {scenario_name}")
    print(f"{'='*80}")

    with tempfile.TemporaryDirectory() as tmpdir:
        # Create app directory structure
        app_dir = Path(tmpdir) / "app" / "api"
        app_dir.mkdir(parents=True)

        test_dir = Path(tmpdir) / "tests"
        test_dir.mkdir(parents=True)

        # Write the code file
        code_file = app_dir / "test_endpoint.py"
        code_file.write_text(code)

        # Optionally write a test file
        if has_test:
            test_file = test_dir / "test_api_endpoint.py"
            test_file.write_text("""
def test_update_employee():
    assert True
""")

        # Initialize git repo
        subprocess.run(["git", "init"], cwd=tmpdir, capture_output=True)
        subprocess.run(["git", "add", "."], cwd=tmpdir, capture_output=True)

        # Run the hook
        result = subprocess.run(
            [sys.executable, str(Path(__file__).parent / "check_write_capabilities.py"), str(code_file)],
            cwd=tmpdir,
            capture_output=True,
            text=True,
        )

        print("\nCode being checked:")
        print("-" * 80)
        print(code)
        print("-" * 80)

        print("\nHook Output:")
        print(result.stdout)
        if result.stderr:
            print("Errors:", result.stderr)

        print(f"\nExit Code: {result.returncode}")
        print(f"Has Test: {has_test}")

        return result.returncode


def main():
    print("Testing Write Capability Detection Hook")

    # Scenario 1: DB mutation without test
    code1 = """
from sqlalchemy.orm import Session
from app.models.employee import Employee

def update_employee_salary(db: Session, emp_id: int, salary: int):
    emp = db.query(Employee).filter(Employee.id == emp_id).first()
    emp.salary = salary
    db.commit()
"""
    create_test_scenario("DB Mutation Without Test", code1, has_test=False)

    # Scenario 2: DB mutation with test
    create_test_scenario("DB Mutation With Test", code1, has_test=True)

    # Scenario 3: HTTP endpoint without test
    code3 = """
from fastapi import APIRouter

router = APIRouter()

@router.put("/employee/{employee_id}")
def update_employee(employee_id: int, payload: dict):
    # Update logic here
    return {"status": "updated"}
"""
    create_test_scenario("HTTP PUT Endpoint Without Test", code3, has_test=False)

    # Scenario 4: Create function without test
    code4 = """
from sqlalchemy.orm import Session
from app.models.employee import Employee

def create_employee(db: Session, name: str, email: str):
    emp = Employee(name=name, email=email, role="employee")
    db.add(emp)
    db.commit()
    return emp
"""
    create_test_scenario("Create Function Without Test", code4, has_test=False)

    # Scenario 5: Delete function without test
    code5 = """
from sqlalchemy.orm import Session
from app.models.employee import Employee

def delete_employee(db: Session, emp_id: int):
    emp = db.query(Employee).filter(Employee.id == emp_id).first()
    db.delete(emp)
    db.commit()
"""
    create_test_scenario("Delete Function Without Test", code5, has_test=False)

    # Scenario 6: Read-only operation (should pass)
    code6 = """
from sqlalchemy.orm import Session
from app.models.employee import Employee

def get_employee(db: Session, emp_id: int):
    return db.query(Employee).filter(Employee.id == emp_id).first()
"""
    result = create_test_scenario("Read-Only Operation (Should Pass)", code6, has_test=False)

    print("\n" + "="*80)
    print("Test Summary")
    print("="*80)
    print("\nThe hook should:")
    print("✓ Flag mutations without tests")
    print("✓ Allow mutations with tests")
    print("✓ Allow read-only operations")
    print("\nRun this script to verify hook behavior during development.")


if __name__ == "__main__":
    main()
