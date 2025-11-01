# campaign-cli/tests/cli/test_backward_compatibility.py
import pytest
import subprocess
import sys
from click.testing import CliRunner
from campaign_cli.cli import build


def test_legacy_portal_flag_mapping():
    """Test that --portal flag maps to --portals and issues warning"""
    runner = CliRunner()
    
    # Test that legacy --portal maps to --portals and shows warning
    result = runner.invoke(build, ['--portal', 'nowandforeverphoto', '--buyer-filter', 'non-buyers'])
    
    # Should succeed (generates empty CSV) and show deprecation warnings
    assert result.exit_code == 0
    assert 'WARNING: --portal is deprecated' in result.output
    assert 'WARNING: --buyer-filter is deprecated' in result.output


def test_legacy_buyer_filter_flag_mapping():
    """Test that --buyer-filter flag maps to audience flags and issues warning"""
    runner = CliRunner()
    
    # Test buyers mapping
    result = runner.invoke(build, ['--portals', 'nowandforeverphoto', '--buyer-filter', 'buyers'])
    assert result.exit_code == 0
    assert 'WARNING: --buyer-filter is deprecated' in result.output
    
    # Test non-buyers mapping  
    result = runner.invoke(build, ['--portals', 'nowandforeverphoto', '--buyer-filter', 'non-buyers'])
    assert result.exit_code == 0
    assert 'WARNING: --buyer-filter is deprecated' in result.output
    
    # Test both mapping
    result = runner.invoke(build, ['--portals', 'nowandforeverphoto', '--buyer-filter', 'both'])
    assert result.exit_code == 0
    assert 'WARNING: --buyer-filter is deprecated' in result.output


def test_conflicting_flags_error():
    """Test that using both legacy and new flags causes error"""
    runner = CliRunner()
    
    # Test portal vs portals conflict
    result = runner.invoke(build, ['--portal', 'test', '--portals', 'test2'])
    assert result.exit_code != 0
    assert 'Cannot use both --portal and --portals' in result.output
    
    # Test buyer-filter vs audience flags conflict
    result = runner.invoke(build, ['--portals', 'test', '--buyer-filter', 'buyers', '--non-buyers'])
    assert result.exit_code != 0
    assert 'Cannot use both --buyer-filter and audience flags' in result.output