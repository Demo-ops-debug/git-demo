import unittest
from unittest.mock import MagicMock
from Tooplateaws import get_default_vpc_and_subnets

# test_Tooplateaws.py


class TestGetDefaultVpcAndSubnets(unittest.TestCase):
    def setUp(self):
        self.mock_client = MagicMock()

    def test_returns_vpc_and_two_subnets(self):
        self.mock_client.describe_vpcs.return_value = {
            'Vpcs': [{'VpcId': 'vpc-12345'}]
        }
        self.mock_client.describe_subnets.return_value = {
            'Subnets': [
                {'SubnetId': 'subnet-1'},
                {'SubnetId': 'subnet-2'},
                {'SubnetId': 'subnet-3'}
            ]
        }
        vpc_id, subnet_ids = get_default_vpc_and_subnets(self.mock_client)
        self.assertEqual(vpc_id, 'vpc-12345')
        self.assertEqual(subnet_ids, ['subnet-1', 'subnet-2'])

    def test_returns_vpc_and_one_subnet(self):
        self.mock_client.describe_vpcs.return_value = {
            'Vpcs': [{'VpcId': 'vpc-abcde'}]
        }
        self.mock_client.describe_subnets.return_value = {
            'Subnets': [
                {'SubnetId': 'subnet-x'}
            ]
        }
        vpc_id, subnet_ids = get_default_vpc_and_subnets(self.mock_client)
        self.assertEqual(vpc_id, 'vpc-abcde')
        self.assertEqual(subnet_ids, ['subnet-x'])

    def test_raises_if_no_vpcs(self):
        self.mock_client.describe_vpcs.return_value = {'Vpcs': []}
        with self.assertRaises(IndexError):
            get_default_vpc_and_subnets(self.mock_client)

    def test_raises_if_no_subnets(self):
        self.mock_client.describe_vpcs.return_value = {
            'Vpcs': [{'VpcId': 'vpc-xyz'}]
        }
        self.mock_client.describe_subnets.return_value = {'Subnets': []}
        vpc_id, subnet_ids = get_default_vpc_and_subnets(self.mock_client)
        self.assertEqual(vpc_id, 'vpc-xyz')
        self.assertEqual(subnet_ids, [])

if __name__ == '__main__':
    unittest.main()