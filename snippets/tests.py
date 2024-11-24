from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from snippets.models import AuditLog, Snippet, SoftDeleteUser as User
from rest_framework_simplejwt.tokens import RefreshToken


class UserManagementAPITests(APITestCase):
    def setUp(self):
        # Create a staff user and a normal user
        self.staff_user = User.objects.create_user(
            username="staffuser",
            email="staff@example.com",
            password="password",
            is_staff=True,
        )
        self.normal_user = User.objects.create_user(
            username="normaluser", email="normal@example.com", password="password"
        )
        self.soft_deleted_user = User.objects.create_user(
            username="deleteduser",
            email="deleted@example.com",
            password="password",
            is_deleted=True,
        )

        # Create tokens for both users
        self.normal_user_token = str(
            RefreshToken.for_user(self.normal_user).access_token
        )
        self.staff_user_token = str(RefreshToken.for_user(self.staff_user).access_token)

        # User create URL
        self.user_create_url = reverse("user-list")
        # User detail URL
        self.user_detail_url = lambda user_id: reverse("user-detail", args=[user_id])

    def test_list_users_as_staff(self):
        self.client.credentials(HTTP_AUTHORIZATION="Bearer " + self.staff_user_token)
        response = self.client.get(reverse("user-list") + "?include_deleted=true")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        usernames = [user["username"] for user in response.data["results"]]
        self.assertIn("staffuser", usernames)
        self.assertIn("normaluser", usernames)
        self.assertIn("deleteduser", usernames)

    def test_list_users_as_normal_user(self):
        self.client.credentials(HTTP_AUTHORIZATION="Bearer " + self.normal_user_token)
        response = self.client.get(reverse("user-list"))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_user_as_normal_user(self):
        # Authenticate as normal user
        self.client.credentials(HTTP_AUTHORIZATION="Bearer " + self.normal_user_token)

        # Attempt to create a new user
        data = {
            "username": "newuser",
            "password": "newpassword",
        }
        response = self.client.post(self.user_create_url, data)

        # Verify that normal users cannot create new users
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_user_as_staff_user(self):
        # Authenticate as staff user
        self.client.credentials(HTTP_AUTHORIZATION="Bearer " + self.staff_user_token)

        # Attempt to create a new user
        data = {
            "username": "newuser",
            "password": "newpassword",
        }
        response = self.client.post(self.user_create_url, data)

        # Verify that staff users can create new users
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_retrieve_user_as_staff(self):
        self.client.credentials(HTTP_AUTHORIZATION="Bearer " + self.staff_user_token)

        # Retrieve a non-deleted user
        response = self.client.get(reverse("user-detail", args=[self.normal_user.id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["username"], "normaluser")

        # Retrieve a soft-deleted user as staff with include_deleted=true
        url = reverse("user-detail", args=[self.soft_deleted_user.id])
        response = self.client.get(f"{url}?include_deleted=true")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["username"], "deleteduser")

    def test_retrieve_user_as_normal_user(self):
        self.client.credentials(HTTP_AUTHORIZATION="Bearer " + self.normal_user_token)

        # Normal user can retrieve non-deleted user
        response = self.client.get(reverse("user-detail", args=[self.staff_user.id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["username"], "staffuser")

        # Normal user cannot retrieve a soft-deleted user
        response = self.client.get(
            reverse("user-detail", args=[self.soft_deleted_user.id])
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_update_user_as_normal_user(self):
        # Authenticate as normal user
        self.client.credentials(HTTP_AUTHORIZATION="Bearer " + self.normal_user_token)

        # Attempt to update the staff user
        data = {
            "username": "updatedstaffuser",
        }
        response = self.client.put(self.user_detail_url(self.staff_user.id), data)

        # Verify that normal users cannot update users
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_update_user_as_staff_user(self):
        # Authenticate as staff user
        self.client.credentials(HTTP_AUTHORIZATION="Bearer " + self.staff_user_token)

        # Attempt to update the normal user
        data = {
            "username": "updatednormaluser",
        }
        response = self.client.put(self.user_detail_url(self.normal_user.id), data)

        # Verify that staff users can update users
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            User.objects.get(id=self.normal_user.id).username, "updatednormaluser"
        )

    def test_soft_delete_user_as_staff(self):
        self.client.credentials(HTTP_AUTHORIZATION="Bearer " + self.staff_user_token)
        response = self.client.delete(
            reverse("user-detail", args=[self.normal_user.id])
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # Ensure the user is marked as soft-deleted
        self.normal_user.refresh_from_db()
        self.assertTrue(self.normal_user.is_deleted)

    def test_soft_delete_user_as_normal_user(self):
        self.client.credentials(HTTP_AUTHORIZATION="Bearer " + self.normal_user_token)
        response = self.client.delete(reverse("user-detail", args=[self.staff_user.id]))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_restore_soft_deleted_user_as_staff(self):
        self.client.credentials(HTTP_AUTHORIZATION="Bearer " + self.staff_user_token)

        # Soft delete the user
        self.soft_deleted_user.is_deleted = True
        self.soft_deleted_user.save()

        # Restore the user
        self.soft_deleted_user.is_deleted = False
        self.soft_deleted_user.save()

        response = self.client.get(reverse("user-list") + "?include_deleted=true")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        usernames = [user["username"] for user in response.data["results"]]
        self.assertIn("deleteduser", usernames)


class AuditLogTests(APITestCase):

    def setUp(self):
        # Create staff and normal users
        self.staff_user = User.objects.create_user(
            username="staff", password="password", is_staff=True
        )
        self.normal_user = User.objects.create_user(
            username="normal", password="password"
        )

        # Log in as the normal user
        self.client.login(username="normal", password="password")

    def test_create_audit_log(self):
        # Use the API to create a snippet
        response = self.client.post(
            reverse("snippet-list"),
            {"title": "Test Snippet", "code": "print('Hello')"},
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Verify the AuditLog entry
        logs = AuditLog.objects.filter(action="create", model_name="Snippet")
        self.assertEqual(logs.count(), 1)
        self.assertEqual(logs.first().user, self.normal_user)

    def test_update_audit_log(self):
        # Create a snippet
        snippet = Snippet.objects.create(
            title="Test Snippet", code="print('Hello')", owner=self.normal_user
        )

        # Use the API to update the snippet
        response = self.client.put(
            reverse("snippet-detail", args=[snippet.id]),
            {"title": "Updated Title", "code": "print('Hello, world!')"},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify the AuditLog entry
        logs = AuditLog.objects.filter(action="update", model_name="Snippet")
        self.assertEqual(logs.count(), 1)
        self.assertEqual(logs.first().user, self.normal_user)

    def test_delete_audit_log(self):
        # Create a snippet
        snippet = Snippet.objects.create(
            title="Test Snippet", code="print('Hello')", owner=self.normal_user
        )

        # Use the API to delete the snippet
        response = self.client.delete(reverse("snippet-detail", args=[snippet.id]))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # Verify the AuditLog entry
        logs = AuditLog.objects.filter(action="destroy", model_name="Snippet")
        self.assertEqual(logs.count(), 1)
        self.assertEqual(logs.first().user, self.normal_user)

    def test_soft_delete_user_audit_log(self):
        # Log in as the staff user
        self.client.login(username="staff", password="password")

        # Use the API to soft delete the normal user
        response = self.client.delete(
            reverse("user-detail", args=[self.normal_user.id])
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        logs = AuditLog.objects.filter(action="destroy", model_name="SoftDeleteUser")
        self.assertEqual(logs.count(), 1)
        self.assertEqual(logs.first().user, self.staff_user)

    def test_list_audit_logs_as_staff(self):
        # Log in as the staff user
        self.client.login(username="staff", password="password")

        # Use the API to retrieve audit logs
        response = self.client.get(reverse("auditlog-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify the response contains audit logs
        self.assertIsInstance(response.data, dict)
        self.assertIn("results", response.data)
        self.assertIsInstance(response.data["results"], list)


class AuthTests(APITestCase):

    def setUp(self):
        self.staff_user = User.objects.create_user(
            username="staff", password="password", is_staff=True
        )
        self.normal_user = User.objects.create_user(
            username="normal", password="password", is_staff=False
        )

    def test_get_user_list_as_staff_using_jwt(self):
        # Get a JWT token for the staff user
        refresh = RefreshToken.for_user(self.staff_user)
        access_token = str(refresh.access_token)

        # Authenticate using the JWT token
        self.client.credentials(HTTP_AUTHORIZATION="Bearer " + access_token)

        # Make a request to the user list endpoint
        response = self.client.get(reverse("user-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_get_user_list_as_normal_user_using_jwt(self):
        # Get a JWT token for the normal user
        refresh = RefreshToken.for_user(self.normal_user)
        access_token = str(refresh.access_token)

        # Authenticate using the JWT token
        self.client.credentials(HTTP_AUTHORIZATION="Bearer " + access_token)

        # Make a request to the user list endpoint (should fail because only staff can access)
        response = self.client.get(reverse("user-list"))
        print(response.data)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_user_as_normal_user(self):
        # Authenticate as normal user
        refresh = RefreshToken.for_user(self.normal_user)
        access_token = str(refresh.access_token)
        self.client.credentials(HTTP_AUTHORIZATION="Bearer " + access_token)

        # Attempt to create a new user
        data = {
            "username": "newuser",
            "password": "newpassword",
        }
        response = self.client.post(reverse("user-list"), data)

        # Verify that normal users cannot create new users
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_user_as_staff_user(self):
        # Authenticate as staff user
        refresh = RefreshToken.for_user(self.staff_user)
        access_token = str(refresh.access_token)
        self.client.credentials(HTTP_AUTHORIZATION="Bearer " + access_token)

        # Attempt to create a new user
        data = {
            "username": "newuser",
            "password": "newpassword",
        }
        response = self.client.post(reverse("user-list"), data)

        # Verify that staff users can create new users
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_update_user_as_normal_user(self):
        # Authenticate as normal user
        refresh = RefreshToken.for_user(self.normal_user)
        access_token = str(refresh.access_token)
        self.client.credentials(HTTP_AUTHORIZATION="Bearer " + access_token)

        # Attempt to update the staff user
        data = {
            "username": "updatedstaffuser",
        }
        response = self.client.put(
            reverse("user-detail", args=[self.staff_user.id]), data
        )

        # Verify that normal users cannot update users
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_update_user_as_staff_user(self):
        # Authenticate as staff user
        refresh = RefreshToken.for_user(self.staff_user)
        access_token = str(refresh.access_token)
        self.client.credentials(HTTP_AUTHORIZATION="Bearer " + access_token)

        # Attempt to update the normal user
        data = {
            "username": "updatednormaluser",
        }
        response = self.client.put(
            reverse("user-detail", args=[self.normal_user.id]), data
        )

        # Verify that staff users can update users
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            User.objects.get(id=self.normal_user.id).username, "updatednormaluser"
        )

    def test_delete_user_as_normal_user(self):
        # Authenticate as normal user
        refresh = RefreshToken.for_user(self.normal_user)
        access_token = str(refresh.access_token)
        self.client.credentials(HTTP_AUTHORIZATION="Bearer " + access_token)

        # Attempt to delete the staff user
        response = self.client.delete(reverse("user-detail", args=[self.staff_user.id]))

        # Verify that normal users cannot delete users
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_delete_user_as_staff_user(self):
        # Authenticate as staff user
        refresh = RefreshToken.for_user(self.staff_user)
        access_token = str(refresh.access_token)
        self.client.credentials(HTTP_AUTHORIZATION="Bearer " + access_token)

        # Attempt to delete the normal user
        response = self.client.delete(
            reverse("user-detail", args=[self.normal_user.id])
        )

        # Verify that staff users can delete users (soft delete)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertTrue(User.objects.get(id=self.normal_user.id).is_deleted)
