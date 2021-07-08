from setuptools import setup
import os

package_name = 'controlserver'

def get_dirs(root=""):
    files = []
    for i, j, k in os.walk(root):
        dirf = [os.path.join(i, pp) for pp in k]
        files.extend(dirf)

    filesdict = {}
    for f in files:
        dir = os.path.split(f)[0]
        if "lib/" + dir not in filesdict:
            filesdict["lib/" + dir] = [f]
        else:
            filesdict["lib/" + dir].append(f)
    # print(list(zip(filesdict.keys(),filesdict.values())))
    return list(zip(filesdict.keys(), filesdict.values()))
data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),

    ]
data_files.extend(get_dirs(package_name))
setup(
    name=package_name,
    version='0.0.0',
    packages=[package_name],
    data_files=data_files,
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='fandes',
    maintainer_email='fandes@todo.todo',
    description='TODO: Package description',
    license='TODO: License declaration',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
	'controller=controlserver.Carwebsocketserver:main',
        ],
    },
)
